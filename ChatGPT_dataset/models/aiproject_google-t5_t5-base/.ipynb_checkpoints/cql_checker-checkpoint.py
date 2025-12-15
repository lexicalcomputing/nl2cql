# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

import lark

def generate_structures(structures):
    for structure in structures:
        yield f"""
        structure_{structure[0]}: /{structure[0]}/ (space)* ( ({"|".join(["/" + s + "/" for s in structure[1]])}) (space)*  (/=/|/==/|/!=/) (space)* value )*
        """

class CQLChecker:
    def __init__(self, token_attributes = ("word", "tag", "lemma", "lc", "lempos_lc", "lempos", "lemma_lc"), structures = (("s", ("audio", )), ("g", ()), ("p", ()), ("u", ()), ("sp", ("who", )), ("vocal", ("desc", )), ("bncdoc", ("alltyp", "wridom", "sdesex", "sdeage", "year", "sporeg", "wriase", "writas", "alltim", "info", "alltim", "genre", "scgdom", "sporeg")))) -> None:
        self.grammar = f"""
            start: (match)* (/&/ (space)* global_conditions)?
            match: (token|space|structure|default_attr|function_meet|function_union|/\\|/) | /\\(/ (space)* (match)+ (space)* /\\)/ (space)* (repetition)? | (space)* match keyword match (space)* | (space)* match /within *\\d+/
            space: / /
            keyword: (space)* /!?within|!?containing/ (space)*
            function_meet: (space)* /\\( *meet/ (space)* token (space)* token (space)*  /-?\\d+ *-?\\d+ *\\)/
            function_union: (space)* /\\( *union/ (space)* function_meet (space)* function_meet (space)* /\\)/

            default_attr: /"[^"]*/ /"/ (space)* (repetition)? | thesaurus

            marker: /\\d+/ (space)* /:/ (space)*
            token: (marker)? /!?\\[/ token_limits_brackets /\\]/ (space)* (repetition)?
            token_limits_brackets: token_limits | (space)* /\\(/ (space)* token_limits (space)* /\\)/ (space)*
            token_limits: (space)* ((token_attribute_value|token_functions|thesaurus|token_limits_brackets) (logic_operator (token_attribute_value|token_functions|thesaurus|token_limits_brackets))*)?

            token_attribute_value: (space)* (/!/)? (space)* token_attribute (space)* (/=/|/==/|/!=/) (space)* value (space)* | (space)* /\\(/ (space)* token_attribute_value (space)* logic_operator (space)* token_attribute_value (space)* /\\)/ (space)*
            value: /"[^"]*/ /"/
            token_attribute: {"|".join([f"/{attr}/" for attr in token_attributes])}
            repetition: /\\?/ | /{{/ (space)* /\\d+/ ((space)* /,/ ((space)* /\\d+/)? )? (space)* /}}/ | /\\*/ | /\\+/ | /{{ *, *\\d+ *}}/
            logic_operator: (space)* (/\\|/ | /&/) (space)*

            structure: ( /< *\\/?/  (space)* ({"|".join([f"structure_{structure[0]}" for structure in structures])}) (space)* />/ ) | ( /</  (space)* ({"|".join([f"structure_{structure[0]}" for structure in structures])}) (space)* /\\/ *>/ )

            {"".join(list(generate_structures(structures)))}

            token_functions: wordsketch|term|exact_pos
            wordsketch: (space)* /ws\\([^\\)]*\\)/ (space)*
            term: (space)* /term\\([^\\)]*\\)/ (space)*
            exact_pos: (space)* (/#\\d+-\\d+|#\\d+/) (space)*

            thesaurus: /!? *~\\d*"[^"]*/ /"/

            global_conditions: global_condition (logic_operator global_condition)*
            global_condition: global_condition_simple (space)* (/=|==|>=?|<=?|=>|=<|!=/) (space)* global_condition_simple | (global_condition_function|global_condition_number) (space)* (/=|==|>=?|<=?|=>|=<|!=/) (space)* (global_condition_function|global_condition_number)
            global_condition_number: (space)* /\\d+/ (space)*
            global_condition_function: /f/ (space)* /\\(/ (space)* /\\d+\\./ token_attribute (space)* /\\)/
            global_condition_simple: (space)* /\\d+\\./ token_attribute (space)*
        """
        self.parser = lark.Lark(self.grammar, lexer="dynamic")

    def parse(self, text: str) -> None:
        self.parser.parse(text)
