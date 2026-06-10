import sys
import math
import time
import random
from typing import Any, List, Callable, Dict


class ExitException(Exception):
    """程式呼叫 exit() 時拋出，攜帶結束碼供 REPL 優雅處理"""
    def __init__(self, code: int):
        super().__init__(f"Program exited with return value {code}.")
        self.code = code


class BuiltinsFunctions:
    """處理 C 語言內建函式與 Python 環境的橋接"""
    
    def __init__(self, memory):
        self.memory = memory
        # 31 個標準內建函式
        self.functions: Dict[str, Callable] = {
            # I/O
            'printf':     self.c_printf,
            'scanf':      self.c_scanf,
            'putchar':    self.c_putchar,
            'getchar':    self.c_getchar,
            'puts':       self.c_puts,
            # 字串
            'strlen':     self.c_strlen,
            'strcmp':     self.c_strcmp,
            'strcpy':     self.c_strcpy,
            'strcat':     self.c_strcat,
            # 數學
            'abs':        self.c_abs,
            'max':        self.c_max,
            'min':        self.c_min,
            'pow':        self.c_pow,
            'sqrt':       self.c_sqrt,
            'mod':        self.c_mod,
            'sin':        self.c_sin,
            'cos':        self.c_cos,
            'tan':        self.c_tan,
            'rand':       self.c_rand,
            'srand':      self.c_srand,
            # 字元判斷
            'isalpha':    self.c_isalpha,
            'isdigit':    self.c_isdigit,
            # 轉換
            'atoi':       self.c_atoi,
            'itoa':       self.c_itoa,
            # 記憶體與工具
            'memset':     self.c_memset,
            'sizeof_int': self.c_sizeof_int,
            'sizeof_char':self.c_sizeof_char,
            'malloc':     self.c_malloc,
            'free':       self.c_free,
            # 系統
            'time':       self.c_time,
            'exit':       self.c_exit,
        }

    # === 記憶體字串輔助工具 ===
    def _read_string(self, addr: int) -> str:
        """從模擬記憶體讀取 C 字串 (直到遇見 \\0)"""
        if addr == 0: return "(null)"
        res = []
        while True:
            c = self.memory.read_char(addr)
            if c == 0: break
            res.append(chr(c))
            addr += 1
        return "".join(res)

    def _write_string(self, addr: int, py_str: str) -> None:
        """將 Python 字串寫入模擬記憶體 (包含結尾 \\0)"""
        for char in py_str:
            self.memory.write_char(addr, ord(char))
            addr += 1
        self.memory.write_char(addr, 0)

    # === 1. I/O 函式 ===
    def c_printf(self, format_ptr: int, *args: int) -> int:
        fmt = self._read_string(format_ptr)
        out_str = ""
        i = 0
        arg_idx = 0
        while i < len(fmt):
            if fmt[i] == '%' and i + 1 < len(fmt):
                char_type = fmt[i + 1]
                if char_type == '%':
                    # %% → 輸出一個 '%'，不消耗引數
                    out_str += '%'
                    i += 2
                    continue
                if arg_idx < len(args):
                    val = args[arg_idx]
                    if char_type == 'd':
                        out_str += str(val)
                    elif char_type == 'c':
                        out_str += chr(val & 0xFF)
                    elif char_type == 's':
                        out_str += self._read_string(val)
                    elif char_type == 'x':
                        # 十六進位小寫，模擬 C 的 unsigned 解釋
                        out_str += format(val & 0xFFFFFFFF, 'x')
                    elif char_type == 'X':
                        out_str += format(val & 0xFFFFFFFF, 'X')
                    else:
                        out_str += f"%{char_type}"   # 未知格式碼原樣輸出
                    arg_idx += 1
                i += 2
            else:
                out_str += fmt[i]
                i += 1
        print(out_str, end='')
        return len(out_str)

    def c_puts(self, str_ptr: int) -> int:
        """輸出字串並自動換行"""
        print(self._read_string(str_ptr))
        return 0

    def c_scanf(self, format_ptr: int, *args: int) -> int:
        fmt = self._read_string(format_ptr)
        user_input = input().split()
        count = 0
        for i, val_str in enumerate(user_input):
            if i >= len(args): break
            self.memory.write_int(args[i], int(val_str))
            count += 1
        return count

    def c_putchar(self, c: int) -> int:
        sys.stdout.write(chr(c))
        return c

    def c_getchar(self) -> int:
        c = sys.stdin.read(1)
        return ord(c) if c else -1

    # === 2. 字串函式 ===
    def c_strlen(self, str_ptr: int) -> int:
        return len(self._read_string(str_ptr))

    def c_strcmp(self, str1_ptr: int, str2_ptr: int) -> int:
        s1 = self._read_string(str1_ptr)
        s2 = self._read_string(str2_ptr)
        return 0 if s1 == s2 else (1 if s1 > s2 else -1)

    def c_strcpy(self, dest_ptr: int, src_ptr: int) -> int:
        s = self._read_string(src_ptr)
        self._write_string(dest_ptr, s)
        return dest_ptr

    def c_strcat(self, dest_ptr: int, src_ptr: int) -> int:
        s1 = self._read_string(dest_ptr)
        s2 = self._read_string(src_ptr)
        self._write_string(dest_ptr, s1 + s2)
        return dest_ptr

    # === 3. 數學與轉換函式 ===
    def c_abs(self, x: int) -> int: return abs(x)
    def c_max(self, a: int, b: int) -> int: return a if a > b else b
    def c_min(self, a: int, b: int) -> int: return a if a < b else b
    def c_pow(self, x: int, y: int) -> int:
        if y < 0: return 0          # 負指數整數除法結果為 0
        if y == 0: return 1
        return int(math.pow(x, y))
    def c_sqrt(self, x: int) -> int:
        if x < 0:
            raise RuntimeError("sqrt() argument must be non-negative")
        return int(math.sqrt(x))
    def c_mod(self, a: int, b: int) -> int:
        """與 % 運算子等效的函式形式；b=0 時拋出執行期錯誤"""
        if b == 0:
            raise ZeroDivisionError("mod() divisor must not be zero")
        remainder = abs(a) % abs(b)
        return -remainder if a < 0 else remainder
    def c_sin(self, x: int) -> int: return int(math.sin(x))
    def c_cos(self, x: int) -> int: return int(math.cos(x))
    def c_tan(self, x: int) -> int: return int(math.tan(x))
    
    def c_atoi(self, str_ptr: int) -> int:
        try: return int(self._read_string(str_ptr).strip())
        except ValueError: return 0

    def c_itoa(self, value: int, str_ptr: int) -> int:
        """整數轉十進位字串，存入 str_ptr 所指的 char 陣列"""
        s = str(value)
        for idx, ch in enumerate(s):
            self.memory.write_char(str_ptr + idx, ord(ch))
        self.memory.write_char(str_ptr + len(s), 0)
        return 0    # void

    def c_isalpha(self, c: int) -> int: return 1 if chr(c & 0xFF).isalpha() else 0
    def c_isdigit(self, c: int) -> int: return 1 if chr(c & 0xFF).isdigit() else 0

    # === 4. 記憶體與工具函式 ===
    def c_memset(self, ptr: int, value: int, size: int) -> int:
        """將 ptr 起始的 size 個位元組全部設為 value 的低 8 位元"""
        byte_val = value & 0xFF
        signed_byte = byte_val if byte_val <= 127 else byte_val - 256
        for i in range(size):
            self.memory.write_char(ptr + i, signed_byte)
        return ptr

    def c_sizeof_int(self) -> int:  return 4
    def c_sizeof_char(self) -> int: return 1

    # === 5. 系統與時間函式 ===
    def c_rand(self) -> int: return random.randint(0, 32767)
    def c_srand(self, seed: int) -> int: random.seed(seed); return 0
    def c_time(self, ptr: int) -> int: return int(time.time())

    def c_malloc(self, size: int) -> int:
        """模擬動態配置：從全域 Data Segment 向上配置 (簡易版 Heap)"""
        try:
            return self.memory.alloc_global(size)
        except Exception:
            return 0    # 記憶體不足回傳 NULL

    def c_free(self, ptr: int) -> int:
        """free 需複雜的 Heap 表；此處為專題簡化，不執行實質回收"""
        return 0

    def c_exit(self, code: int) -> int:
        """立即終止程式，攜帶結束碼"""
        raise ExitException(code)