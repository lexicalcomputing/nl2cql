# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

from typing import Dict, Optional
import requests
import urllib
import html2text


def get_corpinfo_prompt(corpname, corpinfo) -> Dict[str, str]:

    if corpname == "__other__":
        corpinfo = {
            "attributes": "",
            "annotations": "",
            "annotations_full": "",
            "lempos_suffixes": "",
            "structures_and_attributes": "",
            "language": "",
            "gramrels": "",
        }
        return corpinfo

    response = corpinfo

    attributes = "Corpus attributes:\n"
    for attrib in response["attributes"]:
        attrib_label = attrib["label"]
        if len(attrib_label) == 0:
            attrib_label = attrib["name"]
        attributes += f'structure {attrib["name"]} which represents {attrib_label}"\n'

    annotations = "Corpus annotations:\n"
    for annot in response["wposlist"]:
        annotations += f'annotation {annot[0]} is "{annot[1]}"\n'

    tagsetdoc_url = response["tagsetdoc"]
    response_tagsetdoc = requests.get(tagsetdoc_url)
    if response_tagsetdoc.status_code == 200:
        h2t = html2text.HTML2Text()
        h2t.ignore_links = True
        annotations_full = h2t.handle(response_tagsetdoc.text)
    else:
        annotations_full = tagsetdoc_url

    lempos_suffixes = "Lempos suffixes:\n"
    for annot in response["lposlist"]:
        annotations += f'lempos "{annot[0]}" is "{annot[1]}"\n'

    structures_and_attributes = "Following structures and attributes are present in the corpus:\n"
    for struct in response["structures"]:
        struct_label = struct["label"]
        if len(struct_label) == 0:
            struct_label = struct["name"]
        structures_and_attributes += f'structure "{struct["name"]}" which represents {struct_label}"\n'
        for atrib in struct["attributes"]:
            atrib_label = atrib["label"]
            if len(atrib_label) == 0:
                atrib_label = struct["name"]
            structures_and_attributes += f'structure "{struct["name"]}" has attribute "{atrib["name"]}" which represents {atrib_label}"\n'

    gramrels = ["Possible word sketch relations:"]
    for g in response["gramrels"]:
        if isinstance(g, str):
            gramrels.append(g)

    f_lang = response["lang"]
    language = f"The corpus is in {f_lang} language.\n"

    corpinfo = {
        "attributes": attributes,
        "annotations": annotations,
        "annotations_full": annotations_full,
        "lempos_suffixes": lempos_suffixes,
        "structures_and_attributes": structures_and_attributes,
        "language": language,
        "gramrels": "\n".join(gramrels),
    }
    return corpinfo
