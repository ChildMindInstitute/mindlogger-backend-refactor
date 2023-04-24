import asyncio
import json

from apps.migrate.dependencies import (
    get_jsonld_model_converter,
    get_document_loader,
    get_context_resolver,
)


def get_json(filename):
    with open(filename) as fp:
        return json.load(fp)


# jld_url = 'https://raw.githubusercontent.com/ReproNim/demo-protocol/master/DemoProtocol/DemoProtocol_schema'
# jld_url = 'https://raw.githubusercontent.com/ReproNim/reproschema/master/examples/protocols/protocol1_embed.jsonld'
# jld_url = 'https://raw.githubusercontent.com/ReproNim/reproschema/master/examples/protocols/protocol1.jsonld'
# jld_url = 'https://raw.githubusercontent.com/ChildMindInstitute/stability_touch_applet_schema/9d41479807888bd9d72dbbcca2930d099bbd80f9/protocols/stability/stability_schema'
# jld_url = 'https://raw.githubusercontent.com/ReproNim/reproschema-library/master/activities/PHQ-9/items/phq9_category'
jld_url = 'https://raw.githubusercontent.com/hotavocado/HBN_EMA_NIMH2/master/protocols/EMA_HBN_NIMH2/EMA_HBN_NIMH2_schema'


async def main():
    document_loader = get_document_loader()
    context_resolver = get_context_resolver(document_loader)
    converter = get_jsonld_model_converter(document_loader, context_resolver)

    # doc = get_json("ld_repro_example.json")
    # doc = get_json("/Users/ushviachko/work/ChildMind/mindlogger-backend-refactor/_tmp_docs/media/protocols/schema.json")

    # doc = {'_id': ObjectId('5ef14aa5cf98a62237946010'), 'name': '/mindlogger-demo_schema (373)', 'description': '', 'parentCollection': 'collection', 'baseParentId': ObjectId('5ea689a286d25a5dbb14e82c'), 'baseParentType': 'collection', 'parentId': ObjectId('5ea689a286d25a5dbb14e82c'), 'creatorId': ObjectId('5ef14941cf98a6223794600e'), 'created': datetime.datetime(2020, 6, 23, 0, 19, 48, 668000), 'updated': datetime.datetime(2022, 11, 13, 8, 49, 37, 87000), 'size': 1557, 'meta': {'protocol': {'_id': 'protocol/5ea7175c86d25a5dbb14ea29', 'url': 'https://raw.githubusercontent.com/ReproNim/reproschema/master/protocols/mindlogger-demo/mindlogger-demo_schema', 'activities': ['5ea7175d86d25a5dbb14ea2a'], 'activityFlows': []}, 'applet': {'_id': 'applet/5ef14aa5cf98a62237946010'}, 'schema': '1.0.1'}, 'appletName': 'https://raw.githubusercontent.com/ReproNim/reproschema/master/protocols/mindlogger-demo/mindlogger-demo_schema/', 'accountId': ObjectId('5ef14941cf98a6223794600f'), 'access': {'users': [{'id': ObjectId('5ef14941cf98a6223794600e'), 'level': 2, 'flags': []}], 'groups': [{'id': ObjectId('5ef14aa5cf98a62237946011'), 'level': 0, 'flags': []}, {'id': ObjectId('5ef14aa5cf98a62237946012'), 'level': 2, 'flags': []}, {'id': ObjectId('5ef14aa5cf98a62237946013'), 'level': 1, 'flags': []}, {'id': ObjectId('5ef14aa5cf98a62237946014'), 'level': 2, 'flags': []}, {'id': ObjectId('5ef14aa5cf98a62237946015'), 'level': 0, 'flags': []}]}, 'public': True, 'lowerName': '/mindlogger-demo_schema (373)', 'roles': {'user': {'groups': [{'id': ObjectId('5ef14aa5cf98a62237946011'), 'subject': None}]}, 'coordinator': {'groups': [{'id': ObjectId('5ef14aa5cf98a62237946012')}]}, 'editor': {'groups': [{'id': ObjectId('5ef14aa5cf98a62237946013')}]}, 'manager': {'groups': [{'id': ObjectId('5ef14aa5cf98a62237946014')}]}, 'reviewer': {'groups': [{'id': ObjectId('5ef14aa5cf98a62237946015'), 'subject': None}]}}, 'displayName': 'MindLogger Demo', 'cached': ObjectId('62d5a6f0759c7d6caf665003')}

    doc = get_json("src/apps/migrate/applet_test_refactor.json")

    base_url = 'https://raw.githubusercontent.com/ReproNim/demo-protocol/master/DemoProtocol/DemoProtocol_schema'

    protocol = await converter.convert(doc)
    # protocol = await converter.convert(jld_url)

    print(protocol)

asyncio.run(main())
