# repl.py
import os
import sys
from typing import List, Optional

from lexer import Lexer
from parser import Parser, preprocess
from memory import MemoryManager
from symtable import SymbolTable
from interpreter import Interpreter

class REPL:
    """互動式讀取、求值、輸出迴圈 (Read-Eval-Print Loop)"""

    def __init__(self):
        self.source_lines: List[str] = []
        self.trace_mode: bool = False
        self.last_interpreter: Optional[Interpreter] = None
        self.is_dirty: bool = False
        self._interactive_buffer: List[str] = []   # 多行輸入緩衝
        self._tracker = None                       # stdout 換行追蹤器
        self._reset_interactive()                  # 建立持久互動式直譯器

    # ------------------------------------------------------------------
    # 互動式直譯器輔助方法
    # ------------------------------------------------------------------

    def _reset_interactive(self) -> None:
        """建立/重置互動式直譯器（程式啟動或 NEW 指令時呼叫）"""
        mem = MemoryManager()
        sym = SymbolTable(mem)
        self.interactive_interp = Interpreter(mem, sym)

    def _brace_depth(self, lines: List[str]) -> int:
        """計算程式碼行列的淨大括號深度，自動略過字串與註解中的括號。
        depth > 0 表示還有未閉合的區塊，需繼續收集輸入。"""
        depth = 0
        source = '\n'.join(lines)
        i = 0
        n = len(source)
        while i < n:
            c = source[i]
            if c == '"':                            # 字串常數，跳到結尾
                i += 1
                while i < n:
                    if source[i] == '\\':  i += 2; continue
                    if source[i] == '"':   i += 1; break
                    i += 1
                continue
            if c == "'":                            # 字元常數，跳到結尾
                i += 1
                while i < n:
                    if source[i] == '\\':  i += 2; continue
                    if source[i] == "'":   i += 1; break
                    i += 1
                continue
            if c == '/' and i + 1 < n and source[i+1] == '/':   # 單行註解
                while i < n and source[i] != '\n': i += 1
                continue
            if c == '/' and i + 1 < n and source[i+1] == '*':   # 多行註解
                i += 2
                while i < n - 1:
                    if source[i] == '*' and source[i+1] == '/': i += 2; break
                    i += 1
                continue
            if   c == '{': depth += 1
            elif c == '}': depth -= 1
            i += 1
        return depth

    def _execute_interactive(self, source: str) -> None:
        """預處理 → 詞法分析 → 互動式解析 → 在持久狀態中執行。
        若執行後互動直譯器內已有狀態，供後續 VARS/FUNCS 指令查詢。"""
        try:
            source = preprocess(source)
            if not source.strip():
                return
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse_interactive()
            self.interactive_interp.execute_interactive(ast)
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except Exception as e:
            print(f"Runtime error: {e}")

    def print_help(self) -> None:
        print("\n=== 可用指令 (不分大小寫) ===")
        print("  LOAD <檔案>    : 從本機載入 .c 原始碼檔案")
        print("  SAVE <檔案>    : 將緩衝區的程式碼儲存至檔案")
        print("  LIST [n|n1-n2] : 顯示目前緩衝區的程式碼與行號 (可指定行號或範圍)")
        print("  EDIT <n>       : 編輯指定的行號內容")
        print("  DELETE <n|n-m> : 刪除指定的行號或範圍")
        print("  INSERT <n>     : 於指定行號前進入插入模式 (輸入單獨的 '.' 結束)")
        print("  APPEND         : 於緩衝區末尾進入插入模式 (輸入單獨的 '.' 結束)")
        print("  NEW            : 清空緩衝區與執行狀態")
        print("  RUN            : 編譯並執行目前緩衝區的程式")
        print("  CHECK          : 執行語法與語意檢查但不執行")
        print("  TRACE ON/OFF   : 開啟/關閉 AST 節點追蹤模式")
        print("  VARS           : 顯示執行後的全域變數狀態與記憶體位址")
        print("  FUNCS          : 顯示已註冊的函式清單與簽章")
        print("  ABOUT          : 顯示系統與作者資訊")
        print("  HELP           : 顯示此說明文件")
        print("  CLEAR          : 清除終端機畫面")
        print("  EXIT / QUIT    : 離開系統\n")

    def do_about(self) -> None:
        print("\n=========================================")
        print("  Small-C Interactive Interpreter")
        print("  Version: 1.0")
        print("  Author: System Software Student")
        print("  Semester: Spring 2026")
        print("=========================================\n")

    def do_load(self, filepath: str) -> None:
        if not filepath:
            print("[錯誤] 請指定檔案名稱。")
            return
        if self.is_dirty:
            ans = input("[系統] 緩衝區有未儲存的修改，載入新檔將覆蓋目前內容。確定要繼續嗎？(y/n): ")
            if ans.lower() != 'y': return
            
        if not os.path.exists(filepath):
            print(f"[錯誤] 找不到檔案: {filepath}")
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.source_lines = f.read().splitlines()
            self.is_dirty = False
            print(f"[系統] 成功載入 {len(self.source_lines)} 行程式碼。")
        except Exception as e:
            print(f"[錯誤] 讀取檔案失敗: {e}")

    def do_save(self, filepath: str) -> None:
        if not filepath:
            print("[錯誤] 請指定檔案名稱。")
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.source_lines))
            self.is_dirty = False
            print(f"[系統] 程式碼已儲存至 {filepath}")
        except Exception as e:
            print(f"[錯誤] 儲存檔案失敗: {e}")

    def do_list(self, args: str) -> None:
        if not self.source_lines:
            print("[系統] 緩衝區目前是空的。")
            return
            
        start, end = 1, len(self.source_lines)
        if args:
            try:
                if '-' in args:
                    parts = args.split('-')
                    start, end = int(parts[0]), int(parts[1])
                else:
                    start = end = int(args)
            except ValueError:
                print("[錯誤] 無效的行號格式。應為 n 或 n1-n2。")
                return

        start = max(1, start)
        end = min(len(self.source_lines), end)

        if start > end:
            print("[錯誤] 起始行號大於結束行號。")
            return

        print("\n=== 目前程式碼 ===")
        for i in range(start - 1, end):
            print(f"{i + 1:3d}: {self.source_lines[i]}")
        print("==================\n")

    def do_edit(self, args: str) -> None:
        try:
            line_num = int(args)
            if 1 <= line_num <= len(self.source_lines):
                current_line = self.source_lines[line_num - 1]
                print(f"{line_num:3d}: {current_line}")
                new_line = input(f"{line_num:3d}: ")
                if new_line: # 使用者若直接按 Enter (空字串)，則保留原狀
                    self.source_lines[line_num - 1] = new_line
                    self.is_dirty = True
            else:
                print(f"[錯誤] 行號 {line_num} 超出緩衝區範圍。")
        except ValueError:
            print("[錯誤] 請提供有效的行號。")

    def do_delete(self, args: str) -> None:
        if not args:
            print("[錯誤] 請提供要刪除的行號 (如 DELETE 5 或 DELETE 2-4)。")
            return
        try:
            if '-' in args:
                parts = args.split('-')
                start, end = int(parts[0]), int(parts[1])
            else:
                start = end = int(args)
            
            if 1 <= start <= end <= len(self.source_lines):
                del self.source_lines[start - 1:end]
                self.is_dirty = True
                print(f"[系統] 已刪除第 {start} 至 {end} 行。")
            else:
                print("[錯誤] 行號超出範圍。")
        except ValueError:
            print("[錯誤] 請提供有效的行號格式。")

    def do_insert(self, args: str) -> None:
        try:
            line_num = int(args)
            if 1 <= line_num <= len(self.source_lines) + 1:
                new_lines = []
                insert_idx = line_num
                while True:
                    line = input(f"{insert_idx:3d}> ")
                    if line == '.':
                        break
                    new_lines.append(line)
                    insert_idx += 1
                
                if new_lines:
                    self.source_lines[line_num - 1:line_num - 1] = new_lines
                    self.is_dirty = True
            else:
                print(f"[錯誤] 行號 {line_num} 超出範圍。")
        except ValueError:
            print("[錯誤] 請提供有效的行號。")

    def do_append(self) -> None:
        insert_idx = len(self.source_lines) + 1
        new_lines = []
        while True:
            line = input(f"{insert_idx:3d}> ")
            if line == '.':
                break
            new_lines.append(line)
            insert_idx += 1
            
        if new_lines:
            self.source_lines.extend(new_lines)
            self.is_dirty = True

    def do_new(self) -> None:
        if self.is_dirty:
            ans = input("[系統] 緩衝區有未儲存的修改，確定要清除嗎？(y/n): ")
            if ans.lower() != 'y': return

        self.source_lines.clear()
        self.last_interpreter = None
        self._interactive_buffer = []   # 清除多行緩衝
        self.is_dirty = False
        self._reset_interactive()       # 同時重置互動式直譯器狀態
        print("All cleared.")

    def do_check(self) -> None:
        source = "\n".join(self.source_lines)
        if not source.strip():
            print("[系統] 緩衝區為空，無程式碼可檢查。")
            return

        try:
            source = preprocess(source)          # #define 替換
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            parser.parse_program()
            print("No errors found.")
        except SyntaxError as e:
            msg = str(e)
            # parser 的新格式："line N: ..."，補齊成 "Error at line N: ..."
            if msg.startswith('line '):
                print(f"Error at {msg}.")
            else:
                print(f"Error: {msg}")
            print("1 error(s) found.")
        except Exception as e:
            print(f"Error: {e}")
            print("1 error(s) found.")

    def do_run(self) -> None:
        source = "\n".join(self.source_lines)
        if not source.strip():
            print("[系統] 沒有可執行的程式碼，請先輸入或使用 LOAD 指令。")
            return

        mem = MemoryManager()
        sym = SymbolTable(mem)
        interpreter = Interpreter(mem, sym)
        
        if self.trace_mode:
            # TRACE 輔助：只對「語句」層節點印出 [line n] <statement>
            _STMT_TYPES = frozenset({
                'VarDecl','ExprStmt','IfStmt','WhileStmt','ForStmt',
                'DoWhileStmt','ReturnStmt','BreakStmt','ContinueStmt','SwitchStmt',
            })

            def _node_line(n) -> int:
                """從節點遞迴搜尋第一個 Token 的行號"""
                if n is None: return 0
                if hasattr(n, 'line') and isinstance(n.line, int) and n.line > 0:
                    return n.line
                for attr in ('token', 'op', 'var_type', 'name', 'return_type'):
                    tok = getattr(n, attr, None)
                    if tok and hasattr(tok, 'line') and tok.line > 0:
                        return tok.line
                for attr in ('condition', 'expr', 'left', 'init'):
                    child = getattr(n, attr, None)
                    if child and hasattr(child, '__dataclass_fields__'):
                        ln = _node_line(child)
                        if ln > 0: return ln
                return 0

            def _node_label(n) -> str:
                cls = type(n).__name__
                if cls == 'VarDecl':
                    ptr = '*' if n.is_pointer else ''
                    arr = f'[{n.array_size}]' if n.is_array else ''
                    ini = ' = ...' if n.init_expr else ''
                    return f"{n.var_type.value} {ptr}{n.name.value}{arr}{ini};"
                if cls == 'ExprStmt':
                    ec = type(n.expr).__name__
                    if ec == 'FuncCall':
                        return f"{n.expr.name.value}(...);"
                    if ec == 'Assign':
                        lhs = getattr(n.expr.left, 'name', '?')
                        return f"{lhs} {n.expr.op.value} ...;"
                    return "<expression>;"
                return {'IfStmt': 'if (...) { ... }',
                        'WhileStmt': 'while (...) { ... }',
                        'ForStmt': 'for (...) { ... }',
                        'DoWhileStmt': 'do { ... } while (...);',
                        'ReturnStmt': 'return ...;',
                        'BreakStmt': 'break;',
                        'ContinueStmt': 'continue;'}.get(cls, cls)

            original_visit = interpreter.visit
            def traced_visit(node):
                if type(node).__name__ in _STMT_TYPES:
                    ln = _node_line(node)
                    lbl = _node_label(node)
                    prefix = f"[line {ln}]" if ln > 0 else "[line ?]"
                    print(f"{prefix} {lbl}")
                return original_visit(node)
            interpreter.visit = traced_visit

        self.last_interpreter = interpreter

        try:
            source = preprocess(source)          # #define 替換
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse_program()
            
            exit_code = interpreter.visit(ast)
            if self._tracker and self._tracker.last_char != '\n':
                print()   # 補換行，避免輸出黏在 "Program exited..." 前面
            print(f"Program exited with return value {exit_code}.")
            
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except Exception as e:
            print(f"Runtime error: {e}")

    def do_vars(self) -> None:
        # 互動式直譯器有變數時優先顯示互動狀態；
        # 互動式完全空白（只做過 RUN）時才顯示最後一次 RUN 的狀態
        has_interactive = bool(self.interactive_interp.symtable.scopes[0])
        interp = self.interactive_interp if has_interactive else (
                 self.last_interpreter if self.last_interpreter else self.interactive_interp)
        symtable = interp.symtable
        memory   = interp.memory
        global_scope = symtable.scopes[0]

        if not global_scope:
            print("  (無宣告任何全域變數)")
            return

        for name, sym in global_scope.items():
            try:
                if sym.is_array:
                    # 陣列：顯示長度與前 10 個元素
                    elems = []
                    elem_size = 4 if sym.base_type == 'int' else 1
                    read = memory.read_int if sym.base_type == 'int' else memory.read_char
                    for k in range(min(sym.array_size, 10)):
                        elems.append(str(read(sym.address + k * elem_size)))
                    suffix = ", ..." if sym.array_size > 10 else ""
                    print(f"  {sym.base_type} {name}[{sym.array_size}] = {{{', '.join(elems)}{suffix}}}")
                elif sym.is_pointer:
                    ptr_val = memory.read_int(sym.address)
                    print(f"  {sym.base_type} *{name} = {ptr_val}  (points to address {ptr_val})")
                elif sym.base_type == 'int':
                    print(f"  int {name} = {memory.read_int(sym.address)}")
                else:
                    val = memory.read_char(sym.address)
                    ch  = chr(val) if 32 <= val <= 126 else '?'
                    print(f"  char {name} = {val} ('{ch}')")
            except Exception as e:
                print(f"  {sym.base_type} {name} = <error: {e}>")

    def do_funcs(self) -> None:
        has_interactive = bool(self.interactive_interp.functions or
                               self.interactive_interp.symtable.scopes[0])
        interp = self.interactive_interp if has_interactive else (
                 self.last_interpreter if self.last_interpreter else self.interactive_interp)
        funcs    = interp.functions
        builtins = interp.builtins.functions

        print("--- user-defined functions ---")
        if not funcs:
            print("  (none)")
        for name, decl in funcs.items():
            params_str = ", ".join(
                [f"{p.var_type.value}{'*' if p.is_pointer else ''} {p.name.value}"
                 for p in decl.params]
            )
            ret = decl.return_type.value
            line = decl.name.line
            print(f"  {ret} {name}({params_str})  [line {line}]")

        print("--- built-in functions ---")
        builtin_sigs = {
            'printf':'void printf(char *fmt, ...)','scanf':'int scanf(char *fmt, ...)',
            'putchar':'int putchar(int ch)','getchar':'int getchar()',
            'puts':'int puts(char *s)',
            'strlen':'int strlen(char *s)','strcpy':'void strcpy(char *dst, char *src)',
            'strcmp':'int strcmp(char *s1, char *s2)','strcat':'void strcat(char *dst, char *src)',
            'abs':'int abs(int x)','max':'int max(int a, int b)','min':'int min(int a, int b)',
            'pow':'int pow(int base, int exp)','sqrt':'int sqrt(int x)',
            'mod':'int mod(int a, int b)','rand':'int rand()','srand':'void srand(int seed)',
            'atoi':'int atoi(char *s)','itoa':'void itoa(int val, char *str)',
            'memset':'void memset(char *ptr, int val, int n)',
            'sizeof_int':'int sizeof_int()','sizeof_char':'int sizeof_char()',
            'exit':'void exit(int code)',
        }
        for name in builtins:
            sig = builtin_sigs.get(name, f"? {name}(...)")
            print(f"  {sig}  [built-in]")

    def start(self) -> None:
        # ── 用 _TrackingStream 包住 stdout，追蹤最後輸出字元 ──────────────
        class _TrackingStream:
            def __init__(self, stream):
                self._s = stream
                self.last_char = '\n'
            def write(self, s):
                if s: self.last_char = s[-1]
                return self._s.write(s)
            def flush(self): return self._s.flush()
            def __getattr__(self, name): return getattr(self._s, name)

        import sys as _sys
        self._tracker = _TrackingStream(_sys.stdout)
        _sys.stdout = self._tracker

        print("Small-C Interactive Interpreter v1.0")
        print("System Software Final Project, Spring 2026")
        print("Type 'HELP' for a list of commands.")

        while True:
            try:
                # 若上一個輸出沒有換行，補換行再印提示符
                if self._tracker.last_char != '\n':
                    self._tracker._s.write('\n')
                    self._tracker.last_char = '\n'

                # 多行模式顯示接續提示符
                prompt = "  > " if self._interactive_buffer else "sc> "
                cmd = input(prompt)

                # ── 多行收集模式 ───────────────────────────────────────────
                if self._interactive_buffer:
                    self._interactive_buffer.append(cmd)
                    if self._brace_depth(self._interactive_buffer) <= 0:
                        code = '\n'.join(self._interactive_buffer)
                        self._interactive_buffer = []
                        self._execute_interactive(code)
                    continue

                raw = cmd.strip()
                if not raw:
                    continue

                # ── 指令解析 ───────────────────────────────────────────────
                parts    = raw.split(maxsplit=1)
                base_cmd = parts[0].upper()
                args     = parts[1].strip() if len(parts) > 1 else ""

                if base_cmd in ("EXIT", "QUIT"):
                    if self.is_dirty:
                        ans = input("[系統] 緩衝區有未儲存的修改，確定要離開嗎？(y/n): ")
                        if ans.lower() != 'y': continue
                    print("Goodbye.")
                    break

                elif base_cmd == "HELP":   self.print_help()
                elif base_cmd == "ABOUT":  self.do_about()
                elif base_cmd == "LIST":   self.do_list(args)
                elif base_cmd == "CLEAR":  os.system('cls' if os.name == 'nt' else 'clear')
                elif base_cmd == "RUN":    self.do_run()
                elif base_cmd == "CHECK":  self.do_check()
                elif base_cmd == "VARS":   self.do_vars()
                elif base_cmd == "FUNCS":  self.do_funcs()
                elif base_cmd == "NEW":    self.do_new()
                elif base_cmd == "EDIT":   self.do_edit(args)
                elif base_cmd == "DELETE": self.do_delete(args)
                elif base_cmd == "INSERT": self.do_insert(args)
                elif base_cmd == "APPEND": self.do_append()
                elif base_cmd == "LOAD":   self.do_load(args)
                elif base_cmd == "SAVE":   self.do_save(args)
                elif base_cmd == "TRACE":
                    if   args.upper() == "ON":  self.trace_mode = True;  print("Trace mode enabled.")
                    elif args.upper() == "OFF": self.trace_mode = False; print("Trace mode disabled.")
                    else: print("[系統] 用法: TRACE ON 或 TRACE OFF")

                else:
                    # ── 互動式 C 程式碼 ────────────────────────────────────
                    self._interactive_buffer.append(raw)
                    if self._brace_depth(self._interactive_buffer) <= 0:
                        code = '\n'.join(self._interactive_buffer)
                        self._interactive_buffer = []
                        self._execute_interactive(code)
                    # depth > 0：繼續等待更多輸入，下次迴圈顯示 '  > '

            except KeyboardInterrupt:
                if self._interactive_buffer:
                    print("\n[系統] 多行輸入已取消。")
                    self._interactive_buffer = []
                else:
                    print("\n[系統] 偵測到中斷訊號。請輸入 QUIT 離開系統。")
            except EOFError:
                print("\nGoodbye.")
                break