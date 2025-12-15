from typing import List
import urllib.parse
import requests
import urllib

class CQLChecker:
    def __init__(self) -> None:
        self.in_squere_bracket = False
        self.in_regex = False
        self.symbol = ""
        self.ignore_tokens: List[int] = []
        self.is_valid = False
        self.eos_token_id = 1
        self.keywords = ["within", "containing"]
        self.attributes = ["tag", "word", "lempos", "lc", "lemma_lc"]
        self.is_attribute_writen = False
        self.structures = ["s"]
        self.is_in_structure = False

    def match_prefix(self, prefix: str, string_list: List[str]) -> bool:
        for s in string_list:
            if s.startswith(prefix):
                return True
        return False

    def add_char(self, c) -> bool:
        if self.is_attribute_writen:
            if c in ["=", " "]:
                if c == "=":
                    self.is_attribute_writen = False
                return True
            return False

        if len(self.symbol) == 0:
            if self.in_regex:
                if c == "\"":
                    self.in_regex = False
                return True
            if c == "\"":
                self.in_regex = True
                return True

            if c == "[":
                if self.in_squere_bracket:
                    return False
                else:
                    self.in_squere_bracket = True
                    self.is_valid = False
                    return True
            if c == "]":
                if self.in_squere_bracket:
                    self.in_squere_bracket = False
                    self.is_valid = True
                    return True
                else:
                    return False
            
        if self.in_squere_bracket:
            if self.match_prefix(self.symbol + c, self.attributes):
                self.symbol += c
                if self.symbol in self.attributes:
                    self.symbol = ""
                    self.is_attribute_writen = True
                return True
            return False
        if self.match_prefix(self.symbol + c, self.keywords):
            self.symbol += c
            if self.symbol in self.keywords:
                self.symbol = ""
                self.is_valid = False
            return True
        return False
    
    def add_string(self, s, token_id = -1000):
        if token_id == self.eos_token_id:
            if self.is_valid:
                return True
            else:
                return False

        if token_id in self.ignore_tokens:
            return True
        
        state = CQLChecker()
        self.copy(state)
        for c in s:
            if not state.add_char(c):
                return False
        state.copy(self)
        return True


    def copy(self, target: "CQLChecker") -> "CQLChecker":
        target.in_squere_bracket = self.in_squere_bracket
        target.in_regex = self.in_regex
        target.symbol = self.symbol
        target.ignore_tokens = self.ignore_tokens[:]
        target.is_valid = self.is_valid
        target.eos_token_id = self.eos_token_id
        target.keywords = self.keywords
        target.attributes = self.attributes
        target.is_attribute_writen = self.is_attribute_writen
        target.structures = self.structures
        target.is_in_structure = self.is_in_structure
        return target
    
class CQLRemoteChecker:
    def __init__(self, corpname: str, api_key: str) -> None:
        self.cql = ""
        self.corpname = urllib.parse.quote_plus(corpname)
        self.eos_token_id = 1
        self.ignore_tokens: List[int] = []
        self.HEADERS = {"accept": "application/json", "Authorization": "Bearer " + api_key}

    def add_string(self, s: str, token_id: int = -1000) -> bool:
        if token_id in self.ignore_tokens:
            return True

        if token_id == self.eos_token_id:
            cql_urlencoded = urllib.parse.quote_plus(self.cql)
        else:
            cql_urlencoded = urllib.parse.quote_plus(self.cql + s)
        response = requests.get(f"https://app.sketchengine.eu/bonito/run.cgi/check_cql?corpname={self.corpname}&cql={cql_urlencoded}&format=json", headers=self.HEADERS).json()
        if "result" in response and response["result"] == "ok":
            self.cql += s
            return True
        if "error" in response and response["error"].startswith("syntax error, unexpected end of file near position "):
            if token_id == self.eos_token_id:
                return False
            self.cql += s
            return True
        if "error" in response and response["error"].startswith("syntax error, unexpected WORD, expecting end of file near position "):
            if token_id == self.eos_token_id:
                return False
            self.cql += s
            return True
        if "error" in response and response["error"].startswith("syntax error, unexpected end of file, expecting REGEXP or EQ near position "):
            if token_id == self.eos_token_id:
                return False
            self.cql += s
            return True
        if "error" in response and response["error"].startswith("syntax error, unexpected end of file, expecting RBRACKET or BIN_OR near position "):
            if token_id == self.eos_token_id:
                return False
            self.cql += s
            return True
        
        return False
