from bson import json_util

from apps.girderformindlogger.models.folder import Folder as FolderModel
from apps.girderformindlogger.models.item import Item as ItemModel
from apps.girderformindlogger.models.protocol import Protocol
from apps.girderformindlogger.utility import jsonld_expander

CONTEXT = {
    "@context": [
        {
            "reprolib": "https://raw.githubusercontent.com/ReproNim/reproschema/master/"  # noqa: E501
        },
        "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json",  # noqa: E501
        {"_id": {"@id": "_:id", "@type": "schema:text"}},
    ],
    "@type": "https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/Protocol",  # noqa: E501
}


def get_versions_from_history(protocolId):
    protocol = Protocol().load(protocolId, force=True)

    # schemaVersion = (
    #     protocol.get("meta", {})
    #     .get("protocol", {})
    #     .get("schema:schemaVersion", None)
    # )
    # currentVersion = (
    #     schemaVersion[0].get("@value", "0.0.0") if schemaVersion else "0.0.0"
    # )

    if "historyId" not in protocol.get("meta", {}):
        return None

    historyFolder = FolderModel().load(
        protocol["meta"]["historyId"], force=True
    )

    if "referenceId" not in historyFolder.get("meta", {}):
        return None

    referencesFolder = FolderModel().load(
        historyFolder["meta"]["referenceId"], force=True
    )

    references = list(ItemModel().find({"folderId": referencesFolder["_id"]}))

    result = {}
    for reference in references:
        history = reference["meta"].get("history")

        if reference["meta"].get("identifier", "") and len(history):
            modelType = reference["meta"].get("modelType", "")

            # to handle old data without modelType in the schema
            if not modelType:
                lastReference = history[len(history) - 1]["reference"]
                if lastReference:
                    modelType = lastReference.split("/")[0]
                else:
                    modelType = (
                        "screen"
                        if "/" in str(reference["meta"]["identifier"])
                        else "activity"
                    )

            for historyItem in history:
                if (
                    historyItem is None
                    or historyItem["reference"] is None
                    or "reference" not in historyItem
                ):
                    continue
                ref = historyItem["reference"].split("/").pop()
                id = str(reference["meta"]["identifier"])
                ver = historyItem["version"]
                if ver not in result:
                    result[ver] = {}
                if modelType not in result[ver]:
                    result[ver][modelType] = []
                result[ver][modelType].append(
                    {"ref": ref, "id": id, "updated": historyItem["updated"]}
                )

    return result


def get_applet_with_activities(content):
    # content = json.loads(content)
    content = json_util.loads(content)
    activities = content["protocol"].get("activities", {})
    cacheIDToActivity = {}

    for activityIRI in dict.keys(activities):
        activity = activities[activityIRI]

        if type(activity) == str:
            cacheId = activities[activityIRI].split("/")[-1]

            if cacheId not in cacheIDToActivity:
                activity = jsonld_expander.loadCache(cacheId)
                cacheIDToActivity[cacheId] = activity

            activities[activityIRI] = cacheIDToActivity[cacheId]

    return content


def get_versions_from_content(protocolId):
    protocol = Protocol().load(protocolId, force=True)
    if "contentId" not in protocol.get("meta", {}):
        return None
    references = list(
        ItemModel().find(
            query={"folderId": protocol["meta"]["contentId"]},
            sort=[("created", 1)],
        )
    )
    result = {}
    for ref in references:
        ver = ref["version"]
        if ref.get("content") is None or ver in result:
            continue
        applet = get_applet_with_activities(ref["content"])
        result[ver] = {"applet": applet, "updated": ref["updated"]}

    return result


def content_to_jsonld(document, old_activities_by_id):
    jsonld = jsonld_expander.expandObj(
        document["contexts"], document["protocol"]["data"]
    )
    jsonld["_id"] = str(document["protocol"]["data"]["_id"])

    activities_by_id = document["protocol"]["activities"]
    empty_activities = []
    for activity in jsonld["reprolib:terms/order"][0]["@list"]:
        a_id = activity["@id"]

        if "reprolib:terms/" in a_id:
            a_id = a_id.split("reprolib:terms/")[1]

        if a_id in old_activities_by_id and (
            a_id not in activities_by_id
            or activities_by_id[a_id]["items"] == {}
        ):
            activities_by_id[a_id] = old_activities_by_id[a_id]

        if activities_by_id[a_id]["items"] == {}:
            for _a_name, _a_value in activities_by_id.items():
                if (
                    _a_value["data"]["_id"]
                    == activities_by_id[a_id]["data"]["_id"]
                    and _a_name != a_id
                    and _a_value.get("items", {}) != {}
                ):
                    activities_by_id[a_id]["items"] = _a_value["items"].copy()
                    break

        if a_id in activities_by_id and (
            "items" in activities_by_id[a_id]
            and activities_by_id[a_id]["items"] != {}
        ):
            activity_doc = activities_by_id[a_id]
            old_activity_doc = old_activities_by_id.get(a_id, {})

            # fix missing contexts
            for context_key in activity_doc["data"]["@context"]:
                initial_context = document["contexts"][
                    list(document["contexts"].keys())[0]
                ]
                if context_key not in document["contexts"]:
                    document["contexts"][context_key] = initial_context

            activity_jsonld = jsonld_expander.expandObj(
                document["contexts"], activity_doc["data"]
            )
            activity_jsonld["_id"] = str(activity_doc["data"]["_id"])
            activity_jsonld[
                "reprolib:terms/reports"
            ] = []  # remove reports conditional logic for history
            # remove item_flow conditional logic for history
            for property in activity_jsonld["reprolib:terms/addProperties"]:
                property["reprolib:terms/isVis"] = [{"@value": True}]

            activity.update(activity_jsonld)

            items_by_id = activity_doc["items"]
            old_items_by_id = old_activity_doc.get("items", {})

            empty_items = []
            for item in activity["reprolib:terms/order"][0]["@list"]:
                i_id = item["@id"]

                if i_id in old_items_by_id and (i_id not in items_by_id):
                    items_by_id[i_id] = old_items_by_id[i_id]
                if i_id in items_by_id:
                    item_doc = items_by_id[i_id]

                    # fix missing contexts
                    for context_key in item_doc["@context"]:
                        initial_context = document["contexts"][
                            list(document["contexts"].keys())[0]
                        ]
                        if context_key not in document["contexts"]:
                            document["contexts"][context_key] = initial_context

                    item_jsonld = jsonld_expander.expandObj(
                        document["contexts"], item_doc
                    )
                    item_jsonld["_id"] = str(item_doc["_id"])
                    item.update(item_jsonld)
                else:
                    empty_items.append(item)

            for item in empty_items:
                activity["reprolib:terms/order"][0]["@list"].remove(item)
        else:
            empty_activities.append(activity)

    if empty_activities:
        for activity in empty_activities:
            jsonld["reprolib:terms/order"][0]["@list"].remove(activity)

    if jsonld.get("reprolib:terms/activityFlowOrder"):
        jsonld["reprolib:terms/activityFlowOrder"][0]["@list"] = []

    jsonld["@context"] = CONTEXT["@context"]
    jsonld["@type"] = CONTEXT["@type"]
    for act in jsonld["reprolib:terms/order"][0]["@list"]:
        act["reprolib:terms/finalSubscale"] = []
        act["reprolib:terms/subScales"] = []

    # print(jsonld)

    return jsonld, activities_by_id
