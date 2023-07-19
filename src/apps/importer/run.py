from bson.objectid import ObjectId
from pyld import jsonld
from pyshacl import validate as shacl_validate

from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.utility import jsonld_expander


def validate_data(data, shape_file_path):
    """Validate an expanded jsonld document against a shape.
    Taken from reproschema-py repo:
    https://github.com/ReproNim/reproschema-py/blob/9cfcef44e83dbfa8064fd54401ffbf7cfbec0641/reproschema/validate.py#L60
    Parameters
    ----------
    data : dict
        Python dictionary containing JSONLD object
    shape_file_path : str
        SHACL file for the document

    Returns
    -------
    conforms: bool
        Whether the document is conformant with the shape
    v_text: str
        Validation information returned by PySHACL

    """
    kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    normalized = jsonld.normalize(data, kwargs)
    data_file_format = "nquads"
    shape_file_format = "turtle"
    conforms, v_graph, v_text = shacl_validate(
        normalized,
        shacl_graph=shape_file_path,
        data_graph_format=data_file_format,
        shacl_graph_format=shape_file_format,
        inference="rdfs",
        debug=False,
        serialize_report_graph=True,
    )
    return conforms, v_text


def main():
    applet = Applet().findOne({"_id": ObjectId("62e1af24acd35a6fa2a0516e")})
    formatted = jsonld_expander.formatLdObject(
        applet, "applet", None, refreshCache=False, reimportFromUrl=False
    )
    conforms, v_text = validate_data(
        formatted["applet"],
        "https://raw.githubusercontent.com/ReproNim/reproschema/master/validation/reproschema-shacl.ttl",  # noqa: E501
    )
    print("conforms", conforms, "v_text", v_text)


if __name__ == "__main__":
    main()
