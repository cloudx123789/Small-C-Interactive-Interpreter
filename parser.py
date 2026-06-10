import enum
import re
from dataclasses import dataclass
from typing import List, Optional, Any
from lexer import Token, TokenType

def preprocess(source: str) -> str:
    """#define 預處理器：掃描所有 #define NAME VALUE 行，建立替換表，
    移除這些行，再對剩餘原始碼執行詞彙邊界替換。"""
    defines: dict = {}
    output_lines = []

    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#define'):
            parts = stripped.split(None, 2)   # ['#define', 'NAME', 'VALUE']
            if len(parts) == 3:
                name, value = parts[1], parts[2].strip()
                defines[name] = value
            # #define NAME (無值) 直接忽略
        else:
            output_lines.append(line)

    result = '\n'.join(output_lines)

    # 詞彙邊界替換：\b 確保 SIZE→8 不會把 MAXSIZE 誤改成 MAX8
    for name, value in defines.items():
        result = re.sub(r'\b' + re.escape(name) + r'\b', value, result)

    return result

# ==========================================
# AST (抽象語法樹) 節點定義
# ==========================================
class ASTNode:
    pass

@dataclass
class NumberLiteral(ASTNode):
    token: Token
    value: int

@dataclass
class StringLiteral(ASTNode):
    token: Token
    value: str

@dataclass
class CharLiteral(ASTNode):
    token: Token
    value: str

@dataclass
class Identifier(ASTNode):
    token: Token
    name: str

@dataclass
class UnaryOp(ASTNode):
    op: Token
    expr: ASTNode
    is_prefix: bool = True  # 用於區分 ++i (前置) 與 i++ (後置)

@dataclass
class BinOp(ASTNode):
    left: ASTNode
    op: Token
    right: ASTNode

@dataclass
class Assign(ASTNode):
    left: ASTNode
    op: Token
    right: ASTNode

@dataclass
class Block(ASTNode):
    statements: List[ASTNode]

@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    true_branch: ASTNode
    false_branch: Optional[ASTNode]
    line: int = 0    # 關鍵字所在行號（預設 0 = 未記錄）

@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: ASTNode
    line: int = 0    # 關鍵字所在行號（預設 0 = 未記錄）

@dataclass
class DoWhileStmt(ASTNode):
    body: ASTNode
    condition: ASTNode
    line: int = 0    # 關鍵字所在行號（預設 0 = 未記錄）

@dataclass
class ForStmt(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    step: Optional[ASTNode]
    body: ASTNode
    line: int = 0    # 關鍵字所在行號（預設 0 = 未記錄）

@dataclass
class CaseNode(ASTNode):
    value: Optional[ASTNode]  # None 代表 default
    body: List[ASTNode]

@dataclass
class SwitchStmt(ASTNode):
    condition: ASTNode
    cases: List[CaseNode]

@dataclass
class BreakStmt(ASTNode):
    token: Token

@dataclass
class ContinueStmt(ASTNode):
    token: Token

@dataclass
class ExprStmt(ASTNode):
    expr: ASTNode
    line: int = 0    # 關鍵字所在行號（預設 0 = 未記錄）

@dataclass
class FuncParam(ASTNode):
    var_type: Token
    name: Token
    is_pointer: bool

@dataclass
class FuncDecl(ASTNode):
    return_type: Token
    name: Token
    params: List[FuncParam]
    body: Block

@dataclass
class ReturnStmt(ASTNode):
    token: Token
    expr: Optional[ASTNode]

@dataclass
class FuncCall(ASTNode):
    name: Token
    args: List[ASTNode]

@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]  # 包含全域變數與函式宣告

@dataclass
class VarDecl(ASTNode):
    var_type: Token
    name: Token
    is_pointer: bool          # <--- 新增：是否為指標 (*)
    is_array: bool            # <--- 新增：是否為陣列 ([])
    array_size: int           # <--- 新增：陣列長度
    init_expr: Optional[ASTNode]

@dataclass
class FuncParam(ASTNode):
    var_type: Token
    name: Token
    is_pointer: bool          # <--- 新增：是否為指標 (*)

@dataclass
class ArrayAccess(ASTNode):   # <--- 新增：陣列索引存取
    array_expr: ASTNode
    index_expr: ASTNode

# ==========================================
# 語法分析器 (Parser)
# ==========================================
class Parser:
    """語法分析器：採用遞迴下降法建立 AST，嚴格遵循 C 語言 13 級優先順序"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token: Token = self.tokens[self.pos] if self.tokens else Token(TokenType.EOF, None, 0, 0)

    def advance(self) -> None:
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(TokenType.EOF, None, 0, 0)

    def eat(self, token_type: TokenType) -> Token:
        if self.current_token.type == token_type:
            tok = self.current_token
            self.advance()
            return tok
        # 將 TokenType 名稱轉為對使用者友善的符號表示
        _friendly = {
            'SEMI': "';'", 'RPAREN': "')'",  'LPAREN': "'('",
            'RBRACE': "'}'", 'LBRACE': "'{'", 'IDENTIFIER': "identifier",
            'RBRACKET': "']'", 'LBRACKET': "'['", 'COLON': "':'",
        }
        exp = _friendly.get(token_type.name, f"'{token_type.name}'")
        got = _friendly.get(self.current_token.type.name,
                            f"'{self.current_token.value}'")
        raise SyntaxError(
            f"line {self.current_token.line}: expected {exp}, got {got}"
        )

    # 優先順序 13: 指定運算 (Assignment) - 右結合
    def parse_expression(self) -> ASTNode:
        return self.parse_assignment()

    def parse_assignment(self) -> ASTNode:
        node = self.parse_logical_or()
        
        assign_ops = (
            TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
            TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.MOD_ASSIGN,
            TokenType.BIT_AND_ASSIGN, TokenType.BIT_OR_ASSIGN, TokenType.BIT_XOR_ASSIGN,
            TokenType.LSHIFT_ASSIGN, TokenType.RSHIFT_ASSIGN
        )
        
        if self.current_token.type in assign_ops:
            op = self.current_token
            self.advance()
            # 右結合：遞迴呼叫 parse_assignment
            right = self.parse_assignment()
            node = Assign(left=node, op=op, right=right)
            
        return node

    # 優先順序 12: 邏輯 OR (||)
    def parse_logical_or(self) -> ASTNode:
        node = self.parse_logical_and()
        while self.current_token.type == TokenType.OR:
            op = self.current_token
            self.advance()
            right = self.parse_logical_and()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 11: 邏輯 AND (&&)
    def parse_logical_and(self) -> ASTNode:
        node = self.parse_bitwise_or()
        while self.current_token.type == TokenType.AND:
            op = self.current_token
            self.advance()
            right = self.parse_bitwise_or()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 10: 位元 OR (|)
    def parse_bitwise_or(self) -> ASTNode:
        node = self.parse_bitwise_xor()
        while self.current_token.type == TokenType.BIT_OR:
            op = self.current_token
            self.advance()
            right = self.parse_bitwise_xor()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 9: 位元 XOR (^)
    def parse_bitwise_xor(self) -> ASTNode:
        node = self.parse_bitwise_and()
        while self.current_token.type == TokenType.BIT_XOR:
            op = self.current_token
            self.advance()
            right = self.parse_bitwise_and()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 8: 位元 AND (&)
    def parse_bitwise_and(self) -> ASTNode:
        node = self.parse_equality()
        while self.current_token.type == TokenType.BIT_AND:
            op = self.current_token
            self.advance()
            right = self.parse_equality()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 7: 相等性 (==, !=)
    def parse_equality(self) -> ASTNode:
        node = self.parse_relational()
        while self.current_token.type in (TokenType.EQ, TokenType.NEQ):
            op = self.current_token
            self.advance()
            right = self.parse_relational()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 6: 關係 (<, <=, >, >=)
    def parse_relational(self) -> ASTNode:
        node = self.parse_shift()
        while self.current_token.type in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op = self.current_token
            self.advance()
            right = self.parse_shift()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 5: 移位 (<<, >>)
    def parse_shift(self) -> ASTNode:
        node = self.parse_additive()
        while self.current_token.type in (TokenType.LSHIFT, TokenType.RSHIFT):
            op = self.current_token
            self.advance()
            right = self.parse_additive()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 4: 加減法 (+, -)
    def parse_additive(self) -> ASTNode:
        node = self.parse_multiplicative()
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current_token
            self.advance()
            right = self.parse_multiplicative()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 3: 乘除餘 (*, /, %)
    def parse_multiplicative(self) -> ASTNode:
        node = self.parse_unary()
        while self.current_token.type in (TokenType.STAR, TokenType.SLASH, TokenType.MOD):
            op = self.current_token
            self.advance()
            right = self.parse_unary()
            node = BinOp(left=node, op=op, right=right)
        return node

    # 優先順序 2: 單元運算 (前置 ++, --, +, -, !, ~, 還有指標 * 與 &)
    def parse_unary(self) -> ASTNode:
        unary_ops = (
            TokenType.PLUS, TokenType.MINUS, TokenType.NOT, TokenType.BIT_NOT,
            TokenType.INCREMENT, TokenType.DECREMENT, TokenType.STAR, TokenType.BIT_AND
        )
        if self.current_token.type in unary_ops:
            op = self.current_token
            self.advance()
            expr = self.parse_unary() # 單元運算子是右結合
            return UnaryOp(op=op, expr=expr, is_prefix=True)
        return self.parse_postfix()

    # 優先順序 1: 基本元素 (常數、變數、括號)
    def parse_primary(self) -> ASTNode:
        token = self.current_token

        if token.type == TokenType.NUMBER:
            self.advance()
            return NumberLiteral(token=token, value=token.value)
        elif token.type == TokenType.CHARACTER:
            self.advance()
            return CharLiteral(token=token, value=token.value)
        elif token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(token=token, value=token.value)
        elif token.type == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(token=token, name=token.value)
        elif token.type == TokenType.LPAREN:
            self.advance()
            node = self.parse_expression()
            self.eat(TokenType.RPAREN)
            return node
        else:
            got = f"'{token.value}'" if token.value is not None else token.type.name
            raise SyntaxError(
                f"line {token.line}: unexpected token {got}, expected expression"
            )
    
    def parse_statement(self) -> ASTNode:
        if self.current_token.type == TokenType.RETURN:
            tok = self.current_token
            self.advance()
            expr = None
            if self.current_token.type != TokenType.SEMI:
                expr = self.parse_expression()
            self.eat(TokenType.SEMI)
            return ReturnStmt(tok, expr)
        
        """解析單一敘述句 (Statement)"""
        if self.current_token.type == TokenType.LBRACE:
            return self.parse_block()
        elif self.current_token.type == TokenType.IF:
            return self.parse_if_stmt()
        elif self.current_token.type == TokenType.WHILE:
            return self.parse_while_stmt()
        elif self.current_token.type == TokenType.FOR:
            return self.parse_for_stmt()
        elif self.current_token.type == TokenType.DO:
            return self.parse_dowhile_stmt()
        elif self.current_token.type == TokenType.SWITCH:
            return self.parse_switch_stmt()
        elif self.current_token.type == TokenType.BREAK:
            tok = self.current_token
            self.advance()
            self.eat(TokenType.SEMI)
            return BreakStmt(tok)
        elif self.current_token.type == TokenType.CONTINUE:
            tok = self.current_token
            self.advance()
            self.eat(TokenType.SEMI)
            return ContinueStmt(tok)
        elif self.current_token.type in (TokenType.INT, TokenType.CHAR):
            return self.parse_var_decl()
        else:
            # 表達式敘述句 (如 a = 5;)
            line = self.current_token.line   # ← 新增
            expr = self.parse_expression()
            self.eat(TokenType.SEMI)
            return ExprStmt(expr, line)      # ← 傳入 line

    def parse_block(self) -> ASTNode:
        self.eat(TokenType.LBRACE)
        statements = []
        while self.current_token.type != TokenType.RBRACE and self.current_token.type != TokenType.EOF:
            statements.append(self.parse_statement())
        self.eat(TokenType.RBRACE)
        return Block(statements)

    def parse_if_stmt(self) -> ASTNode:
        line = self.current_token.line
        self.eat(TokenType.IF)
        self.eat(TokenType.LPAREN)
        cond = self.parse_expression()
        self.eat(TokenType.RPAREN)
        true_branch = self.parse_statement()
        
        false_branch = None
        if self.current_token.type == TokenType.ELSE:
            self.eat(TokenType.ELSE)
            false_branch = self.parse_statement()
            
        return IfStmt(cond, true_branch, false_branch, line)

    def parse_while_stmt(self) -> ASTNode:
        line = self.current_token.line
        self.eat(TokenType.WHILE)
        self.eat(TokenType.LPAREN)
        cond = self.parse_expression()
        self.eat(TokenType.RPAREN)
        body = self.parse_statement()
        return WhileStmt(cond, body, line)

    def parse_dowhile_stmt(self) -> ASTNode:
        line = self.current_token.line
        self.eat(TokenType.DO)
        body = self.parse_statement()
        self.eat(TokenType.WHILE)
        self.eat(TokenType.LPAREN)
        cond = self.parse_expression()
        self.eat(TokenType.RPAREN)
        self.eat(TokenType.SEMI)
        return DoWhileStmt(body, cond, line)

    def parse_for_stmt(self) -> ASTNode:
        line = self.current_token.line
        self.eat(TokenType.FOR)
        self.eat(TokenType.LPAREN)
        
        # 1. 初始化區段
        init_node = None
        if self.current_token.type != TokenType.SEMI:
            if self.current_token.type in (TokenType.INT, TokenType.CHAR):
                init_node = self.parse_var_decl() # VarDecl 自帶分號
            else:
                init_node = ExprStmt(self.parse_expression())
                self.eat(TokenType.SEMI)
        else:
            self.eat(TokenType.SEMI)
            
        # 2. 條件區段
        cond_node = None
        if self.current_token.type != TokenType.SEMI:
            cond_node = self.parse_expression()
        self.eat(TokenType.SEMI)
        
        # 3. 步進區段
        step_node = None
        if self.current_token.type != TokenType.RPAREN:
            step_node = ExprStmt(self.parse_expression())
        self.eat(TokenType.RPAREN)
        
        body = self.parse_statement()
        return ForStmt(init_node, cond_node, step_node, body)

    def parse_switch_stmt(self) -> ASTNode:
        """解析 Switch/Case (支援 Fall-through)"""
        self.eat(TokenType.SWITCH)
        self.eat(TokenType.LPAREN)
        cond = self.parse_expression()
        self.eat(TokenType.RPAREN)
        self.eat(TokenType.LBRACE)
        
        cases: List[CaseNode] = []
        while self.current_token.type in (TokenType.CASE, TokenType.DEFAULT):
            if self.current_token.type == TokenType.CASE:
                self.eat(TokenType.CASE)
                val_expr = self.parse_expression()
                self.eat(TokenType.COLON)
                
                body = []
                # 持續讀取直到遇到下一個 case, default 或是 switch 結束
                while self.current_token.type not in (TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                    body.append(self.parse_statement())
                cases.append(CaseNode(value=val_expr, body=body))
                
            elif self.current_token.type == TokenType.DEFAULT:
                self.eat(TokenType.DEFAULT)
                self.eat(TokenType.COLON)
                
                body = []
                while self.current_token.type not in (TokenType.CASE, TokenType.DEFAULT, TokenType.RBRACE):
                    body.append(self.parse_statement())
                cases.append(CaseNode(value=None, body=body))
                
        self.eat(TokenType.RBRACE)
        return SwitchStmt(cond, cases)

    # 【更新】優先順序 1.5 函式呼叫 (Postfix)
    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        
        # 處理函式呼叫 func_name(...)
        if self.current_token.type == TokenType.LPAREN and isinstance(node, Identifier):
            self.eat(TokenType.LPAREN)
            args = []
            if self.current_token.type != TokenType.RPAREN:
                args.append(self.parse_expression())
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    args.append(self.parse_expression())
            self.eat(TokenType.RPAREN)
            node = FuncCall(name=node.token, args=args)
            
        # 處理後置 ++ / --
        elif self.current_token.type in (TokenType.INCREMENT, TokenType.DECREMENT):
            op = self.current_token
            self.advance()
            node = UnaryOp(op=op, expr=node, is_prefix=False)
            
        return node

    # 【新增】解析函式參數
    def parse_func_param(self) -> FuncParam:
        var_type = self.current_token
        self.advance() # INT 或 CHAR
        # TODO: 處理指標 '*'
        name = self.current_token
        self.eat(TokenType.IDENTIFIER)
        return FuncParam(var_type, name)

    # 【新增】解析整體程式碼結構 (Program)
    def parse_program(self) -> Program:
            declarations = []
            while self.current_token.type != TokenType.EOF:
                # 全域層級只允許型別開頭的宣告 (int / char / void)
                if self.current_token.type not in (TokenType.INT, TokenType.CHAR, TokenType.VOID):
                    got = f"'{self.current_token.value}'" if self.current_token.value else self.current_token.type.name
                    raise SyntaxError(
                        f"line {self.current_token.line}: "
                        f"unexpected {got} at global scope, expected type declaration (int/char/void)"
                    )
                # 非破壞性前瞻：略過型別與可能的 '*'，找到識別字後看下一個 token
                # 下一個是 '(' 代表函式定義，否則為全域變數宣告
                look = self.pos + 1
                if look < len(self.tokens) and self.tokens[look].type == TokenType.STAR:
                    look += 1
                after_name = look + 1
                is_function = (after_name < len(self.tokens)
                            and self.tokens[after_name].type == TokenType.LPAREN)
                if is_function:
                    declarations.append(self.parse_func_decl())
                else:
                    declarations.append(self.parse_var_decl())
            return Program(declarations)
    
    def parse_func_decl(self) -> FuncDecl:
        return_type = self.current_token
        self.advance()  # 略過 int / char / void
        name = self.current_token
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LPAREN)
        params = []
        # 支援空參數列，以及 C 風格的 (void) 參數列
        if self.current_token.type == TokenType.VOID:
            self.advance()  # 如 int main(void)，略過 void
        elif self.current_token.type != TokenType.RPAREN:
            params.append(self.parse_func_param())
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                params.append(self.parse_func_param())
        self.eat(TokenType.RPAREN)
        body = self.parse_block()
        return FuncDecl(return_type, name, params, body)

    def parse_var_decl(self) -> ASTNode:
        var_type = self.current_token
        self.advance() # 略過 INT 或 CHAR
        
        is_pointer = False
        if self.current_token.type == TokenType.STAR:
            is_pointer = True
            self.advance()
            
        name_tok = self.current_token
        self.eat(TokenType.IDENTIFIER)
        
        is_array = False
        array_size = 0
        if self.current_token.type == TokenType.LBRACKET:
            is_array = True
            self.advance()
            size_tok = self.current_token
            self.eat(TokenType.NUMBER)
            array_size = size_tok.value
            self.eat(TokenType.RBRACKET)
            
        init_expr = None
        if self.current_token.type == TokenType.ASSIGN:
            self.advance()
            init_expr = self.parse_expression()
            
        self.eat(TokenType.SEMI)
        return VarDecl(var_type, name_tok, is_pointer, is_array, array_size, init_expr)

    def parse_func_param(self) -> FuncParam:
        var_type = self.current_token
        self.advance()
        
        is_pointer = False
        if self.current_token.type == TokenType.STAR:
            is_pointer = True
            self.advance()
            
        name = self.current_token
        self.eat(TokenType.IDENTIFIER)
        
        # 支援參數陣列語法 (如 int arr[])，在 C 語言中它會退化為指標
        if self.current_token.type == TokenType.LBRACKET:
            self.advance()
            self.eat(TokenType.RBRACKET)
            is_pointer = True
            
        return FuncParam(var_type, name, is_pointer)

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        
        # 允許連續的後置操作 (例如 arr[i]++)
        while self.current_token.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.INCREMENT, TokenType.DECREMENT):
            if self.current_token.type == TokenType.LPAREN and isinstance(node, Identifier):
                # 函式呼叫 func_name(...)
                self.eat(TokenType.LPAREN)
                args = []
                if self.current_token.type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token.type == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        args.append(self.parse_expression())
                self.eat(TokenType.RPAREN)
                node = FuncCall(name=node.token, args=args)
                
            elif self.current_token.type == TokenType.LBRACKET:
                # 陣列索引 arr[i]
                self.eat(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.eat(TokenType.RBRACKET)
                node = ArrayAccess(array_expr=node, index_expr=index_expr)
                
            elif self.current_token.type in (TokenType.INCREMENT, TokenType.DECREMENT):
                # 後置遞增/遞減
                op = self.current_token
                self.advance()
                node = UnaryOp(op=op, expr=node, is_prefix=False)
                
        return node
    
    def parse_interactive(self) -> Program:
        #互動模式解析：頂層可出現任意語句、宣告或函式定義的混合。
        declarations = []
        while self.current_token.type != TokenType.EOF:
            if self.current_token.type in (TokenType.INT, TokenType.CHAR, TokenType.VOID):
                # 前瞻判斷：函式定義 vs 變數宣告（與 parse_program 相同邏輯）
                look = self.pos + 1
                if look < len(self.tokens) and self.tokens[look].type == TokenType.STAR:
                    look += 1
                after_name = look + 1
                is_function = (after_name < len(self.tokens) and
                            self.tokens[after_name].type == TokenType.LPAREN)
                if is_function:
                    declarations.append(self.parse_func_decl())
                else:
                    declarations.append(self.parse_var_decl())
            else:
                # 一般語句：賦值、函式呼叫、控制結構等
                declarations.append(self.parse_statement())
        return Program(declarations)