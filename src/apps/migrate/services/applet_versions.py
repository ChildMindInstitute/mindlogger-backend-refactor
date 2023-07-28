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
        ItemModel().find({"folderId": protocol["meta"]["contentId"]})
    )
    result = {}
    for ref in references:
        ver = ref["version"]
        applet = get_applet_with_activities(ref["content"])
        result[ver] = {"applet": applet, "updated": ref["updated"]}

    return result


def content_to_jsonld(document):
    jsonld = jsonld_expander.expandObj(
        document["contexts"], document["protocol"]["data"]
    )

    activities_by_id = document["protocol"]["activities"]
    for activity in jsonld["reprolib:terms/order"][0]["@list"]:
        a_id = activity["@id"]
        if a_id in activities_by_id:
            activity_doc = activities_by_id[a_id]
            activity_jsonld = jsonld_expander.expandObj(
                document["contexts"], activity_doc["data"]
            )
            activity.update(activity_jsonld)

            items_by_id = activity_doc["items"]

            for item in activity["reprolib:terms/order"][0]["@list"]:
                i_id = item["@id"]
                if i_id in items_by_id:
                    item_doc = items_by_id[i_id]
                    item_jsonld = jsonld_expander.expandObj(
                        document["contexts"], item_doc
                    )
                    item.update(item_jsonld)

    # check the same for activity flow
    flows_by_id = document["protocol"]["activityFlows"]
    new_flow_by_id = {}

    for _, flow in flows_by_id.items():
        new_flow_by_id[flow["@id"]] = flow

    for flow in jsonld["reprolib:terms/activityFlowOrder"][0]["@list"]:
        a_id = flow["@id"]
        if a_id in new_flow_by_id:
            flow_doc = new_flow_by_id[a_id]
            flow_jsonld = jsonld_expander.expandObj(
                document["contexts"], flow_doc
            )
            flow.update(flow_jsonld)
    jsonld["@context"] = CONTEXT["@context"]
    jsonld["@type"] = CONTEXT["@type"]

    return jsonld
