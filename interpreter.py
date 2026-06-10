from parser import (
    ASTNode, NumberLiteral, StringLiteral, CharLiteral, Identifier, BinOp, UnaryOp, Assign,
    Block, ExprStmt, VarDecl, IfStmt, WhileStmt, DoWhileStmt, 
    ForStmt, SwitchStmt, BreakStmt, ContinueStmt, CaseNode,
    FuncDecl, FuncCall, ReturnStmt, Program, ArrayAccess # <--- 加入 ArrayAccess, StringLiteral, CharLiteral
)
from lexer import TokenType, Token
from typing import Any, Dict
from symtable import SymbolTable
from memory import MemoryManager
from cbuiltins import BuiltinsFunctions, ExitException

class BreakException(Exception): pass
class ContinueException(Exception): pass
class ReturnException(Exception):
    def __init__(self, value: Any):
        self.value = value

class Interpreter:
    """執行引擎：採用 Visitor 模式走訪 AST 並求值"""
    def __init__(self, memory: MemoryManager, symtable: SymbolTable):
        self.memory = memory
        self.symtable = symtable
        self.builtins = BuiltinsFunctions(self.memory)
        
        # 儲存自定義函式的 AST 節點
        self.functions: Dict[str, FuncDecl] = {}
        
        # 字串常數池：相同字串共用同一塊資料段記憶體 (避免迴圈內重複配置)
        self.string_pool: Dict[str, int] = {}

    def visit(self, node: ASTNode) -> Any:
        """根據 Node 的類別名稱，動態呼叫對應的 visit_ 函式"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode) -> None:
        raise Exception(f"尚未實作該節點的處理邏輯: {type(node).__name__}")

    def visit_NumberLiteral(self, node: NumberLiteral) -> int:
        return node.value

    def _intern_string(self, s: str) -> int:
        """將字串常數寫入模擬記憶體 (資料段)，回傳其起始位址。
        相同字串內容共用同一塊儲存空間 (字串池)，避免迴圈內重複配置而耗盡資料段。"""
        if s in self.string_pool:
            return self.string_pool[s]
        # 配置 len(s)+1 位元組 (尾端保留 '\0')
        addr = self.memory.alloc_global(len(s) + 1)
        for i, ch in enumerate(s):
            self.memory.write_char(addr + i, ord(ch))
        self.memory.write_char(addr + len(s), 0)  # 字串結尾空字元
        self.string_pool[s] = addr
        return addr

    def visit_StringLiteral(self, node: StringLiteral) -> int:
        """字串常數求值：寫入記憶體後回傳「位址」(C 語言中字串即 char* 位址)"""
        return self._intern_string(node.value)

    def visit_CharLiteral(self, node: CharLiteral) -> int:
        """字元常數求值：C 語言中字元常數本質為 int，回傳其 ASCII 整數值"""
        if not node.value:
            return 0
        return ord(node.value[0])

    def visit_BinOp(self, node: BinOp) -> Any:
        # 【關鍵實作】：邏輯短路求值 (Short-Circuit Evaluation)
        if node.op.type == TokenType.AND:
            left_val = self.visit(node.left)
            if not left_val:  # C 語言中 0 為 False
                return 0
            right_val = self.visit(node.right)
            return 1 if right_val else 0
            
        elif node.op.type == TokenType.OR:
            left_val = self.visit(node.left)
            if left_val:
                return 1
            right_val = self.visit(node.right)
            return 1 if right_val else 0

        # 其他算術與關係運算 (兩側皆須求值)
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        
        op_type = node.op.type
        
        # 算術
        if op_type == TokenType.PLUS: return left_val + right_val
        elif op_type == TokenType.MINUS: return left_val - right_val
        elif op_type == TokenType.STAR: return left_val * right_val
        elif op_type == TokenType.SLASH:
            if right_val == 0: raise ZeroDivisionError("division by zero")
            return self._c_div(left_val, right_val)   # 向零截斷，而非 Python // 的向下取整
        elif op_type == TokenType.MOD:
            if right_val == 0: raise ZeroDivisionError("division by zero")
            return self._c_mod(left_val, right_val)   # 餘數符號跟隨被除數
        
        # 關係運算 (回傳 1 為 True, 0 為 False)
        elif op_type == TokenType.EQ: return 1 if left_val == right_val else 0
        elif op_type == TokenType.NEQ: return 1 if left_val != right_val else 0
        elif op_type == TokenType.LT: return 1 if left_val < right_val else 0
        elif op_type == TokenType.LTE: return 1 if left_val <= right_val else 0
        elif op_type == TokenType.GT: return 1 if left_val > right_val else 0
        elif op_type == TokenType.GTE: return 1 if left_val >= right_val else 0
        
        # 位元運算
        elif op_type == TokenType.LSHIFT: return left_val << right_val
        elif op_type == TokenType.RSHIFT: return left_val >> right_val
        elif op_type == TokenType.BIT_AND: return left_val & right_val
        elif op_type == TokenType.BIT_OR: return left_val | right_val
        elif op_type == TokenType.BIT_XOR: return left_val ^ right_val

        raise Exception(f"未知的二元運算子: {op_type.name}")

    def visit_UnaryOp(self, node: UnaryOp) -> Any:
        op_type = node.op.type
        
        # 處理 ++ / --
        if op_type in (TokenType.INCREMENT, TokenType.DECREMENT):
            if not isinstance(node.expr, Identifier):
                raise SyntaxError("遞增/遞減運算子必須應用於變數")
            
            sym = self.symtable.lookup(node.expr.name)
            old_val = self._read_cell(sym.address, sym.base_type, sym.is_pointer)
            new_val = old_val + 1 if op_type == TokenType.INCREMENT else old_val - 1
            self._write_cell(sym.address, sym.base_type, sym.is_pointer, new_val)

            # 前置：回傳新值；後置：回傳舊值
            return new_val if node.is_prefix else old_val

        # 指標取值 (*ptr)：讀取 ptr 所指位址的內容
        if op_type == TokenType.STAR:
            addr, base_type, is_pointer = self.get_lvalue(node)
            return self._read_cell(addr, base_type, is_pointer)

        # 取址 (&x)：回傳運算元的記憶體位址
        if op_type == TokenType.BIT_AND:
            addr, _, _ = self.get_lvalue(node.expr)
            return addr

        # 處理一般單元運算
        val = self.visit(node.expr)
        if op_type == TokenType.PLUS: return +val
        elif op_type == TokenType.MINUS: return -val
        elif op_type == TokenType.NOT: return 0 if val else 1
        elif op_type == TokenType.BIT_NOT: return ~val

        raise Exception(f"未知的單元運算子: {op_type.name}")
    
    def visit_Block(self, node: Block) -> None:
        """進入 Block 時開啟新 Scope，結束時安全釋放記憶體"""
        self.symtable.enter_scope()
        try:
            for stmt in node.statements:
                self.visit(stmt)
        finally:
            self.symtable.leave_scope()

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        self.visit(node.expr)

    def _is_word(self, base_type: str, is_pointer: bool) -> bool:
        """判斷儲存格是否為 4-byte：int 與「任何指標」皆為 4-byte，char 為 1-byte"""
        return is_pointer or base_type == 'int'

    def _read_cell(self, addr: int, base_type: str, is_pointer: bool) -> int:
        """依型別從記憶體讀取一個值"""
        if self._is_word(base_type, is_pointer):
            return self.memory.read_int(addr)
        return self.memory.read_char(addr)

    def _write_cell(self, addr: int, base_type: str, is_pointer: bool, val: int) -> None:
        """依型別將一個值寫入記憶體"""
        if self._is_word(base_type, is_pointer):
            self.memory.write_int(addr, val)
        else:
            # char 為 8-bit 有號數，超出範圍時依 C 語義環繞
            self.memory.write_char(addr, ((val + 128) % 256) - 128)
    
    @staticmethod
    def _c_div(a: int, b: int) -> int:
        """C 語言整數除法：向零截斷。
        Python // 是向負無限大截斷：-15 // 4 = -4，但 C -15/4 = -3。"""
        sign = -1 if (a < 0) != (b < 0) else 1
        return sign * (abs(a) // abs(b))

    @staticmethod
    def _c_mod(a: int, b: int) -> int:
        """C 語言 % 運算：餘數符號與被除數相同。
        如 -7 % 3 在 Python = 2，但 C = -1。"""
        remainder = abs(a) % abs(b)
        return -remainder if a < 0 else remainder

    def visit_VarDecl(self, node: VarDecl) -> None:
        """變數宣告：依型別/指標/陣列向符號表請求正確大小的記憶體並處理初始化"""
        base_type = 'int' if node.var_type.type == TokenType.INT else 'char'
        sym = self.symtable.declare(
            node.name.value, base_type,
            is_pointer=node.is_pointer,
            is_array=node.is_array,
            array_size=node.array_size,
        )
        if node.init_expr is None:
            return

        if node.is_array:
            # 僅支援 char 陣列以字串常數初始化 (如 char s[10] = "hi";)
            if base_type == 'char':
                src = self.visit(node.init_expr)
                i = 0
                while True:
                    c = self.memory.read_char(src + i)
                    self.memory.write_char(sym.address + i, c)
                    if c == 0:
                        break
                    i += 1
            else:
                raise RuntimeError("不支援 int 陣列的初始化列表")
        else:
            val = self.visit(node.init_expr)
            self._write_cell(sym.address, base_type, node.is_pointer, val)

    def visit_Identifier(self, node: Identifier) -> Any:
        """讀取變數值；陣列名稱退化 (decay) 為指向首元素的位址"""
        sym = self.symtable.lookup(node.name)
        if sym.is_array:
            return sym.address
        return self._read_cell(sym.address, sym.base_type, sym.is_pointer)

    def visit_ArrayAccess(self, node: ArrayAccess) -> int:
        """讀取陣列/指標元素 arr[i] 的值"""
        addr, base_type, is_pointer = self.get_lvalue(node)
        return self._read_cell(addr, base_type, is_pointer)

    def visit_Assign(self, node: Assign) -> Any:
        """指定運算：支援對變數、指標取值 (*p)、陣列元素 (arr[i]) 寫入實體記憶體"""
        addr, base_type, is_pointer = self.get_lvalue(node.left)
        right_val = self.visit(node.right)

        if node.op.type == TokenType.ASSIGN:
            final_val = right_val
        else:
            current_val = self._read_cell(addr, base_type, is_pointer)
            op = node.op.type
            if   op == TokenType.PLUS_ASSIGN:     final_val = current_val + right_val
            elif op == TokenType.MINUS_ASSIGN:    final_val = current_val - right_val
            elif op == TokenType.STAR_ASSIGN:     final_val = current_val * right_val
            elif op == TokenType.SLASH_ASSIGN:
                if right_val == 0: raise ZeroDivisionError("division by zero")
                final_val = self._c_div(current_val, right_val)
            elif op == TokenType.MOD_ASSIGN:
                if right_val == 0: raise ZeroDivisionError("division by zero")
                final_val = self._c_mod(current_val, right_val)
            elif op == TokenType.BIT_AND_ASSIGN:  final_val = current_val & right_val
            elif op == TokenType.BIT_OR_ASSIGN:   final_val = current_val | right_val
            elif op == TokenType.BIT_XOR_ASSIGN:  final_val = current_val ^ right_val
            elif op == TokenType.LSHIFT_ASSIGN:   final_val = current_val << right_val
            elif op == TokenType.RSHIFT_ASSIGN:   final_val = current_val >> right_val
            else:
                raise Exception(f"未知的複合指定運算子: {node.op.type}")

        self._write_cell(addr, base_type, is_pointer, final_val)
        return final_val

    def visit_IfStmt(self, node: IfStmt) -> None:
        cond_val = self.visit(node.condition)
        if cond_val:
            self.visit(node.true_branch)
        elif node.false_branch:
            self.visit(node.false_branch)

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        while self.visit(node.condition):
            try:
                self.visit(node.body)
            except BreakException:
                break
            except ContinueException:
                continue

    def visit_DoWhileStmt(self, node: DoWhileStmt) -> None:
        while True:
            try:
                self.visit(node.body)
            except BreakException:
                break
            except ContinueException:
                pass
            if not self.visit(node.condition):
                break

    def visit_ForStmt(self, node: ForStmt) -> None:
        # for 迴圈本身的初始化可能宣告變數，需包裝一層 Scope
        self.symtable.enter_scope()
        try:
            if node.init:
                self.visit(node.init)
                
            while True:
                if node.condition and not self.visit(node.condition):
                    break
                try:
                    self.visit(node.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                    
                if node.step:
                    self.visit(node.step)
        finally:
            self.symtable.leave_scope()

    def visit_SwitchStmt(self, node: SwitchStmt) -> None:
        """Switch 核心邏輯：完美實作 C 語言的 Fall-through 特性"""
        switch_val = self.visit(node.condition)
        fall_through = False
        
        try:
            for case_node in node.cases:
                # 判斷是否為 default 或是數值匹配
                is_match = False
                if case_node.value is None:
                    is_match = True  # default case
                else:
                    if self.visit(case_node.value) == switch_val:
                        is_match = True
                        
                if is_match or fall_through:
                    fall_through = True # 觸發 Fall-through 機制
                    # 執行該 case 內的所有敘述
                    for stmt in case_node.body:
                        self.visit(stmt)
        except BreakException:
            # 捕捉到 break，成功逃離 switch 區塊
            pass

    def visit_BreakStmt(self, node: BreakStmt) -> None:
        raise BreakException()

    def visit_ContinueStmt(self, node: ContinueStmt) -> None:
        raise ContinueException()
    
    def visit_Program(self, node: Program) -> int:
        # 第一階段：註冊所有全域變數與函式
        for decl in node.declarations:
            if isinstance(decl, FuncDecl):
                self.functions[decl.name.value] = decl
            else:
                self.visit(decl)
                
        # 第二階段：尋找並執行 main 函式
        if 'main' not in self.functions:
            raise RuntimeError("找不到程式進入點: main()")
            
        main_call = FuncCall(name=Token(TokenType.IDENTIFIER, 'main', 0, 0), args=[])
        try:
            return self.visit(main_call)
        except ExitException as e:
            return e.code
        

    def execute_interactive(self, node: Program) -> None:
        """互動模式執行：逐條處理，維持全域狀態。
        若輸入的整個區塊就是一個完整的 main() 定義，自動呼叫它。"""
        newly_defined = []
        for decl in node.declarations:
            if isinstance(decl, FuncDecl):
                self.functions[decl.name.value] = decl   # 只登記
                newly_defined.append(decl.name.value)
            else:
                self.visit(decl)    # VarDecl / ExprStmt / IfStmt / …

        # 若本次輸入「只定義了 main」（沒有其他語句），自動呼叫 main()
        if newly_defined == ['main']:
            main_call = FuncCall(name=Token(TokenType.IDENTIFIER, 'main', 0, 0), args=[])
            try:
                self.visit(main_call)
            except ExitException as e:
                print(f"Program exited with return value {e.code}.")
            except Exception:
                raise

    # 【新增】函式呼叫與 Call Frame 隔離
    def visit_FuncCall(self, node: FuncCall) -> Any:
        func_name = node.name.value
        
        # 1. 優先計算所有引數 (Arguments) 的值 (必須在當前的 Scope 計算)
        arg_values = [self.visit(arg) for arg in node.args]

        # 2. 檢查是否為內建函式
        if func_name in self.builtins.functions:
            builtin_func = self.builtins.functions[func_name]
            return builtin_func(*arg_values)

        # 3. 自定義函式呼叫
        if func_name not in self.functions:
            raise NameError(f"呼叫未定義的函式: {func_name}")
            
        func_decl = self.functions[func_name]
        
        if len(arg_values) != len(func_decl.params):
            raise TypeError(f"函式 {func_name} 預期 {len(func_decl.params)} 個引數，卻獲得 {len(arg_values)} 個")

        # === 核心魔法：隔離 Call Frame ===
        # 儲存呼叫者的 Scope 狀態
        saved_scopes = self.symtable.scopes
        
        # 建立新的執行緒框架：只能看見 Global (索引 0)
        self.symtable.scopes = [saved_scopes[0]]
        self.symtable.enter_scope() # 進入函式的 Local Scope
        
        ret_val = 0
        try:
            # 綁定參數 (Parameter Binding)
            for param, val in zip(func_decl.params, arg_values):
                base_type = 'int' if param.var_type.type == TokenType.INT else 'char'
                sym = self.symtable.declare(param.name.value, base_type,
                                            is_pointer=param.is_pointer)
                self._write_cell(sym.address, base_type, param.is_pointer, val)

            # 執行函式主體
            self.visit(func_decl.body)
            
        except ReturnException as e:
            ret_val = e.value
        finally:
            self.symtable.leave_scope()
            # 恢復呼叫者的 Scope 狀態
            self.symtable.scopes = saved_scopes
            
        return ret_val

    # 【新增】Return 例外拋出
    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        val = 0
        if node.expr:
            val = self.visit(node.expr)
        raise ReturnException(val)
    
    def _get_sym(self, node: ASTNode):
        """遞迴往下尋找基礎的符號表物件 (Symbol)，用於判斷型別"""
        if isinstance(node, Identifier):
            return self.symtable.lookup(node.name)
        elif isinstance(node, ArrayAccess):
            return self._get_sym(node.array_expr)
        elif isinstance(node, UnaryOp) and node.op.type == TokenType.STAR:
            return self._get_sym(node.expr)
        return None

    def get_lvalue(self, node: ASTNode):
        """核心方法：取得可指定節點的 (記憶體位址, 基礎型別, 是否為指標)"""
        if isinstance(node, Identifier):
            sym = self.symtable.lookup(node.name)
            return sym.address, sym.base_type, sym.is_pointer

        elif isinstance(node, UnaryOp) and node.op.type == TokenType.STAR:
            # *ptr：L-value 是 ptr 內含的位址；元素型別為指標所指型別
            addr = self.visit(node.expr)
            sym = self._get_sym(node.expr)
            base_type = sym.base_type if sym else 'int'
            return addr, base_type, False

        elif isinstance(node, ArrayAccess):
            # arr[i]：基底位址 (陣列退化或指標值) + 索引 * 元素大小
            base_addr = self.visit(node.array_expr)
            index_val = self.visit(node.index_expr)
            sym = self._get_sym(node.array_expr)
            base_type = sym.base_type if sym else 'int'
            # 元素大小只取決於 base_type：int 元素 4 bytes，char 元素 1 byte
            elem_size = 4 if base_type == 'int' else 1

            if sym and sym.is_array and not (0 <= index_val < sym.array_size):
                raise IndexError(
                    f"array index out of bounds (index {index_val}, size {sym.array_size})"
                )
            return base_addr + index_val * elem_size, base_type, False

        else:
            raise SyntaxError("無效的左值 (L-value)，無法被指派或取址")

# ==========================================
# 單元測試模組
# ==========================================
if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    def run(src: str) -> int:
        mem = MemoryManager()
        interp = Interpreter(mem, SymbolTable(mem))
        return interp.visit(Parser(Lexer(src).tokenize()).parse_program())

    print("=== Interpreter 煙霧測試 (指標與陣列) ===")
    run('''
    void swap(int *a, int *b) { int t; t = *a; *a = *b; *b = t; }
    int main() {
        int arr[3];
        arr[0] = 5; arr[1] = 9; arr[2] = 1;
        swap(&arr[0], &arr[2]);
        printf("arr = %d %d %d\\n", arr[0], arr[1], arr[2]);
        return 0;
    }
    ''')
    print("=> 測試完成。")