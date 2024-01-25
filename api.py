from utils import getRequestType
import requests
import logging

LOGGER = logging.getLogger(__name__)


def searchResponse(responseResults, filteredEntityInput: str):
    """
    FUNC NAME: searchResponse
    FUNC DESC: Searches the API response for the user input. Returns empty list if nothing was found
    FUNC TYPE: Function
    """
    # Sets entity name/title to lowercase and removes spaces
    def parse(entityHeader):
        return entityHeader.replace(" ", "").lower()

    matches = []

    for apiEntity in responseResults:

        # Documents don't have a name attribute
        if "title" in apiEntity:

            # Look for a partial match if no exact match can be found. Exact matches are pushed to front
            if filteredEntityInput == parse(apiEntity["title"]):
                matches.insert(0, {"entity": apiEntity, "partial": False})
            elif filteredEntityInput in parse(apiEntity["title"]):
                matches.append({"entity": apiEntity, "partial": True})

        elif "name" in apiEntity:

            if filteredEntityInput == parse(apiEntity["name"]):
                matches.insert(0, {"entity": apiEntity, "partial": False})
            elif filteredEntityInput in parse(apiEntity["name"]):
                matches.append({"entity": apiEntity, "partial": True})

    return matches


def requestScryfall(splitSearchTerm: list):
    """
    FUNC NAME: requestScryfall
    FUNC DESC: Queries the Scryfall API to obtain a thumbnail image.
    FUNC TYPE: Function
    """
    requestStr = f"https://api.scryfall.com/cards/search?q={' '.join(splitSearchTerm)}&include_extras=true&include_multilingual=true&include_variations=true"
    scryfallRequest = requests.get(requestStr)

    # Try again with the first arg if nothing was found
    foundItem = {}
    if scryfallRequest.status_code == 404:
        LOGGER.info(f"Scryfall 1st Attempt - No matches found for: {requestStr}")
        requestStr = f"https://api.scryfall.com/cards/search?q={splitSearchTerm[0]}&include_extras=true&include_multilingual=true&include_variations=true"
        scryfallWordRequest = requests.get(requestStr)

        if scryfallWordRequest.status_code != 200:
            LOGGER.info(f"Scryfall 2nd Attempt - No matches found for: {requestStr}")
            return scryfallWordRequest.status_code
        else:
            foundItem = scryfallWordRequest.json()["data"][0]

    # Return code if API request failed
    elif scryfallRequest.status_code != 200:
        LOGGER.warning(f"Scryfall 1st Attempt - API Request failed for: {requestStr}")
        return scryfallRequest.status_code

    # Otherwise, return the cropped image url
    else:
        foundItem = scryfallRequest.json()["data"][0]
    
    # Verify there is a valid card face and image
    if "card_faces" in foundItem.keys() and len(foundItem["card_faces"]) >= 1:
        foundCardFace = list(foundItem["card_faces"])[0]
        if "image_uris" in foundCardFace.keys() and len(foundCardFace["image_uris"].keys()) >= 1:
            imageUris = dict(foundCardFace["image_uris"])
            if "art_crop" in imageUris.keys():
                return imageUris["art_crop"]
    # Otherwise, no valid image found
    return 404



def requestOpen5e(query: str, filteredEntityInput: str, wideSearch: bool, listResults: bool):
    """
    FUNC NAME: requestOpen5e
    FUNC DESC: Queries the Open5e API and returns an array of results
    FUNC TYPE: Function
    """
    # API Request
    request = requests.get(query)

    # Return code if not successful
    if request.status_code != 200:
        return {"code": request.status_code, "query": query}

    # Iterate through the results
    results = searchResponse(request.json()["results"], filteredEntityInput)

    if results == []:
        # No full or partial matches were found
        return []
    elif listResults is True:
        # Return all the full and partial matches
        return results
    else:
        firstMatchedEntity = results[0]
        if wideSearch is True:
            # Request directory using the first word of the name to filter results
            route = firstMatchedEntity['entity']["route"]

            # Determine filter type (search can only be used for some directories)
            filterType = getRequestType(route)

            if "title" in results:
                directoryRequest = requests.get(
                    f"https://api.open5e.com/{route}?format=json&limit=10000&{filterType}={firstMatchedEntity['entity']['title'].split()[0]}"
                )
            else:
                directoryRequest = requests.get(
                    f"https://api.open5e.com/{route}?format=json&limit=10000&{filterType}={firstMatchedEntity['entity']['name'].split()[0]}"
                )

            # Return code if not successful
            if directoryRequest.status_code != 200:
                return {
                    "code": directoryRequest.status_code,
                    "query": f"https://api.open5e.com/{route}?format=json&limit=10000&search={firstMatchedEntity['entity']['name'].split()[0]}"
                }

            # Search response again for the actual object, return empty array if none was found
            actualMatch = searchResponse(directoryRequest.json()["results"], filteredEntityInput)
            if actualMatch != []:
                actualMatch[0]["route"] = route
                return actualMatch[0]
            else:
                return []
        else:
            # We already got a match, return it
            return firstMatchedEntity


def getOpen5eRoot():
    """
    FUNC NAME: getOpen5eRoot
    FUNC DESC: Retrieves the open5e root dir, which contains the directory urls and names
    FUNC TYPE: Function
    """
    # Get API Root
    rootRequest = requests.get("https://api.open5e.com?format=json")

    if rootRequest.status_code == 200:
        # Remove search directory from list (not used)
        allDirectories = list(rootRequest.json().keys())
        allDirectories.remove("search")
        return allDirectories
    else:
        # Throw if Root request wasn't successful
        LOGGER.error(f"API Request to Open5e root directory FAILED. Code: {rootRequest.status_code}")
        return rootRequest.status_code
