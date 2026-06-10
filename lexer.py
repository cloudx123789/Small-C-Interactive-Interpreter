import enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

class TokenType(enum.Enum):
    # 關鍵字 (Keywords)
    INT = enum.auto()
    CHAR = enum.auto()
    VOID = enum.auto()
    IF = enum.auto()
    ELSE = enum.auto()
    WHILE = enum.auto()
    FOR = enum.auto()
    DO = enum.auto()
    BREAK = enum.auto()
    CONTINUE = enum.auto()
    RETURN = enum.auto()
    SWITCH = enum.auto()
    CASE = enum.auto()
    DEFAULT = enum.auto()
    
    # 前處理器 (Preprocessor)
    DEFINE = enum.auto()      # #define

    # 識別字與字面常數 (Identifiers & Literals)
    IDENTIFIER = enum.auto()
    NUMBER = enum.auto()      # 整數 (10 進位與 16 進位)
    STRING = enum.auto()      # 字串常數
    CHARACTER = enum.auto()   # 字元常數

    # 算術運算子 (Arithmetic Operators)
    PLUS = enum.auto()        # +
    MINUS = enum.auto()       # -
    STAR = enum.auto()        # *
    SLASH = enum.auto()       # /
    MOD = enum.auto()         # %
    INCREMENT = enum.auto()   # ++
    DECREMENT = enum.auto()   # --

    # 關係與邏輯運算子 (Relational & Logical Operators)
    EQ = enum.auto()          # ==
    NEQ = enum.auto()         # !=
    LT = enum.auto()          # <
    LTE = enum.auto()         # <=
    GT = enum.auto()          # >
    GTE = enum.auto()         # >=
    AND = enum.auto()         # &&
    OR = enum.auto()          # ||
    NOT = enum.auto()         # !

    # 位元運算子 (Bitwise Operators)
    BIT_AND = enum.auto()     # &
    BIT_OR = enum.auto()      # |
    BIT_XOR = enum.auto()     # ^
    BIT_NOT = enum.auto()     # ~
    LSHIFT = enum.auto()      # <<
    RSHIFT = enum.auto()      # >>

    # 指定運算子 (Assignment Operators)
    ASSIGN = enum.auto()             # =
    PLUS_ASSIGN = enum.auto()        # +=
    MINUS_ASSIGN = enum.auto()       # -=
    STAR_ASSIGN = enum.auto()        # *=
    SLASH_ASSIGN = enum.auto()       # /=
    MOD_ASSIGN = enum.auto()         # %=
    BIT_AND_ASSIGN = enum.auto()     # &=
    BIT_OR_ASSIGN = enum.auto()      # |=
    BIT_XOR_ASSIGN = enum.auto()     # ^=
    LSHIFT_ASSIGN = enum.auto()      # <<=
    RSHIFT_ASSIGN = enum.auto()      # >>=

    # 符號與括號 (Punctuation)
    LPAREN = enum.auto()      # (
    RPAREN = enum.auto()      # )
    LBRACE = enum.auto()      # {
    RBRACE = enum.auto()      # }
    LBRACKET = enum.auto()    # [
    RBRACKET = enum.auto()    # ]
    SEMI = enum.auto()        # ;
    COMMA = enum.auto()       # ,
    COLON = enum.auto()       # :

    # 檔案結尾 (End of File)
    EOF = enum.auto()


@dataclass
class Token:
    """代表一個語彙單元 (Token)"""
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, line={self.line}, col={self.column})"


class Lexer:
    """語彙分析器：負責將原始碼字元流轉換為 Token 序列"""
    
    # 關鍵字對照表
    KEYWORDS: Dict[str, TokenType] = {
        'int': TokenType.INT,
        'char': TokenType.CHAR,
        'void': TokenType.VOID,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'do': TokenType.DO,
        'break': TokenType.BREAK,
        'continue': TokenType.CONTINUE,
        'return': TokenType.RETURN,
        'switch': TokenType.SWITCH,
        'case': TokenType.CASE,
        'default': TokenType.DEFAULT,
    }

    def __init__(self, source_code: str):
        self.source: str = source_code
        self.position: int = 0
        self.line: int = 1
        self.column: int = 1
        self.current_char: Optional[str] = self.source[0] if self.source else None

    def advance(self) -> None:
        """推進一個字元並更新行列資訊"""
        if self.current_char == '\n':
            self.line += 1
            self.column = 0

        self.position += 1
        if self.position >= len(self.source):
            self.current_char = None
        else:
            self.current_char = self.source[self.position]
            self.column += 1

    def peek(self, offset: int = 1) -> Optional[str]:
        """預讀前方字元，不改變當前狀態"""
        peek_pos = self.position + offset
        if peek_pos >= len(self.source):
            return None
        return self.source[peek_pos]

    def skip_whitespace_and_comments(self) -> None:
        """略過空白字元與單行/多行註解"""
        while self.current_char is not None:
            if self.current_char.isspace():
                self.advance()
            elif self.current_char == '/' and self.peek() == '/':
                # 單行註解
                while self.current_char is not None and self.current_char != '\n':
                    self.advance()
            elif self.current_char == '/' and self.peek() == '*':
                # 多行註解
                self.advance() # 略過 '/'
                self.advance() # 略過 '*'
                while self.current_char is not None:
                    if self.current_char == '*' and self.peek() == '/':
                        self.advance() # 略過 '*'
                        self.advance() # 略過 '/'
                        break
                    self.advance()
            else:
                break

    def lex_number(self) -> Token:
        """解析數字字面常數 (支援十進位與十六進位)"""
        start_col = self.column
        num_str = ""
        
        # 判斷是否為十六進位 (0x 或 0X)
        if self.current_char == '0' and self.peek() in ('x', 'X'):
            num_str += self.current_char
            self.advance()
            num_str += self.current_char
            self.advance()
            while self.current_char is not None and self.current_char.isalnum():
                num_str += self.current_char
                self.advance()
            try:
                val = int(num_str, 16)
            except ValueError:
                raise SyntaxError(f"line {self.line}: invalid hex constant '{num_str}'")
        else:
            # 十進位解析
            while self.current_char is not None and self.current_char.isdigit():
                num_str += self.current_char
                self.advance()
            val = int(num_str)
            
        return Token(TokenType.NUMBER, val, self.line, start_col)

    def lex_escape_char(self) -> str:
        """處理字串或字元中的跳脫序列"""
        self.advance() # 略過 '\\'
        if self.current_char is None:
            raise SyntaxError(f"line {self.line}: unexpected end of input in escape sequence")
        
        char_map = {
            'n': '\n', 't': '\t', 'r': '\r',
            '0': '\0', '\\': '\\', '\'': '\'', '\"': '\"'
        }
        
        escaped_char = char_map.get(self.current_char, self.current_char)
        self.advance()
        return escaped_char

    def lex_string(self) -> Token:
        """解析字串常數"""
        start_col = self.column
        self.advance() # 略過起始的 '"'
        string_val = ""
        
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == '\\':
                string_val += self.lex_escape_char()
            else:
                string_val += self.current_char
                self.advance()
                
        if self.current_char != '"':
            raise SyntaxError(f"line {self.line}: unterminated string constant")
        
        self.advance() # 略過結尾的 '"'
        return Token(TokenType.STRING, string_val, self.line, start_col)

    def lex_char(self) -> Token:
        """解析字元常數"""
        start_col = self.column
        self.advance() # 略過起始的 "'"
        
        char_val = ""
        if self.current_char == '\\':
            char_val = self.lex_escape_char()
        elif self.current_char is not None:
            char_val = self.current_char
            self.advance()
            
        if self.current_char != "'":
            raise SyntaxError(f"line {self.line}: unterminated or invalid character constant")
            
        self.advance() # 略過結尾的 "'"
        # C 語言字元本質為 int，此處我們保留為長度 1 的字串，後續 interpreter 可透過 ord() 處理
        return Token(TokenType.CHARACTER, char_val, self.line, start_col)

    def lex_identifier_or_keyword(self) -> Token:
        """解析識別字、關鍵字與前處理器巨集"""
        start_col = self.column
        id_str = ""
        
        # 處理 #define
        if self.current_char == '#':
            id_str += self.current_char
            self.advance()
            
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            id_str += self.current_char
            self.advance()
            
        if id_str == '#define':
            return Token(TokenType.DEFINE, id_str, self.line, start_col)
        elif id_str.startswith('#'):
            raise SyntaxError(f"line {self.line}: unsupported preprocessor directive '{id_str}'")
            
        token_type = self.KEYWORDS.get(id_str, TokenType.IDENTIFIER)
        return Token(token_type, id_str, self.line, start_col)

    def get_next_token(self) -> Token:
        """取得下一個 Token 的核心邏輯"""
        while self.current_char is not None:
            self.skip_whitespace_and_comments()
            if self.current_char is None:
                break
                
            start_col = self.column
            c = self.current_char

            # 識別字或關鍵字 (支援 #define 開頭)
            if c.isalpha() or c == '_' or c == '#':
                return self.lex_identifier_or_keyword()

            # 數字字面常數
            if c.isdigit():
                return self.lex_number()

            # 字串與字元
            if c == '"':
                return self.lex_string()
            if c == "'":
                return self.lex_char()

            # 運算子與符號 (採用 Maximal Munch 原則)
            # 3-char 運算子
            c3 = self.source[self.position:self.position+3] if self.position + 2 < len(self.source) else ""
            if c3 == '<<=': self.advance(); self.advance(); self.advance(); return Token(TokenType.LSHIFT_ASSIGN, c3, self.line, start_col)
            if c3 == '>>=': self.advance(); self.advance(); self.advance(); return Token(TokenType.RSHIFT_ASSIGN, c3, self.line, start_col)

            # 2-char 運算子
            c2 = self.source[self.position:self.position+2] if self.position + 1 < len(self.source) else ""
            op2_map = {
                '++': TokenType.INCREMENT, '--': TokenType.DECREMENT,
                '==': TokenType.EQ, '!=': TokenType.NEQ,
                '<=': TokenType.LTE, '>=': TokenType.GTE,
                '&&': TokenType.AND, '||': TokenType.OR,
                '+=': TokenType.PLUS_ASSIGN, '-=': TokenType.MINUS_ASSIGN,
                '*=': TokenType.STAR_ASSIGN, '/=': TokenType.SLASH_ASSIGN,
                '%=': TokenType.MOD_ASSIGN, '&=': TokenType.BIT_AND_ASSIGN,
                '|=': TokenType.BIT_OR_ASSIGN, '^=': TokenType.BIT_XOR_ASSIGN,
                '<<': TokenType.LSHIFT, '>>': TokenType.RSHIFT
            }
            if c2 in op2_map:
                self.advance()
                self.advance()
                return Token(op2_map[c2], c2, self.line, start_col)

            # 1-char 運算子與符號
            op1_map = {
                '+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.STAR,
                '/': TokenType.SLASH, '%': TokenType.MOD, '=': TokenType.ASSIGN,
                '<': TokenType.LT, '>': TokenType.GT, '!': TokenType.NOT,
                '&': TokenType.BIT_AND, '|': TokenType.BIT_OR, '^': TokenType.BIT_XOR,
                '~': TokenType.BIT_NOT, '(': TokenType.LPAREN, ')': TokenType.RPAREN,
                '{': TokenType.LBRACE, '}': TokenType.RBRACE, '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET, ';': TokenType.SEMI, ',': TokenType.COMMA,
                ':': TokenType.COLON
            }
            if c in op1_map:
                self.advance()
                return Token(op1_map[c], c, self.line, start_col)

            raise SyntaxError(f"line {self.line}: unknown character '{c}'")

        return Token(TokenType.EOF, None, self.line, self.column)

    def tokenize(self) -> List[Token]:
        """完整掃描並回傳所有 Token"""
        tokens = []
        while True:
            tok = self.get_next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens

# 單元測試模組
if __name__ == "__main__":
    test_source = """
    #define MAX_SIZE 100
    // 這是一個測試程式
    int main() {
        int a = 0x1F;       /* 測試 16 進位 */
        char* str = "Hello\nWorld";
        char c = '\\n';
        
        for (int i = 0; i < MAX_SIZE; i++) {
            if (a == 31 && c != 'x') {
                a <<= 1;
                break;
            }
        }
        
        switch(a) {
            case 1: a += 1; break;
            default: return 0;
        }
        return a;
    }
    """
    
    print("開始執行 Lexer 單元測試...")
    lexer = Lexer(test_source)
    try:
        tokens = lexer.tokenize()
        for token in tokens:
            print(token)
        print("\n=> 單元測試通過，所有 Token 已成功提取。")
    except Exception as e:
        print(f"\n=> 單元測試失敗: {e}")