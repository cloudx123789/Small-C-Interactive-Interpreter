# symtable.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from memory import MemoryManager

@dataclass
class Symbol:
    """代表一個宣告的變數或指標"""
    name: str
    base_type: str        # 'int' 或 'char'
    is_pointer: bool      # 是否為指標 (*)
    is_array: bool        # 是否為陣列 ([])
    array_size: int       # 陣列長度 (若非陣列則為 0)
    address: int          # 在記憶體中的實體位址

    def get_byte_size(self) -> int:
        """計算此符號所需的實體記憶體大小"""
        # Small-C 中，指標一律為 4 bytes
        elem_size = 4 if (self.base_type == 'int' or self.is_pointer) else 1
        return elem_size * self.array_size if self.is_array else elem_size


class SymbolTable:
    """符號表管理：使用環境堆疊 (Scope Stack) 處理生命週期與變數遮蔽 (Shadowing)"""
    
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        # 作用域堆疊，索引 0 為 Global Scope
        self.scopes: List[Dict[str, Symbol]] = [{}]
        # 記錄每次進入區域作用域時的 stack_sp，以便退出時能精準釋放記憶體
        self.scope_sp_history: List[int] = []

    def enter_scope(self) -> None:
        """進入新的 Block (如進入函式、if/while 區塊)"""
        self.scopes.append({})
        self.scope_sp_history.append(self.memory.stack_sp)

    def leave_scope(self) -> None:
        """離開當前 Block，觸發生命週期結束與記憶體回收"""
        if len(self.scopes) <= 1:
            raise RuntimeError("無法離開全域作用域")
            
        self.scopes.pop()
        restore_sp = self.scope_sp_history.pop()
        self.memory.free_locals(restore_sp)

    def declare(self, name: str, base_type: str, is_pointer: bool = False, 
                is_array: bool = False, array_size: int = 0) -> Symbol:
        """在當前作用域宣告新變數，並向 MemoryManager 請求空間"""
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise NameError(f"重複宣告的變數: '{name}'")
            
        sym = Symbol(name, base_type, is_pointer, is_array, array_size, 0)
        size_bytes = sym.get_byte_size()

        if len(self.scopes) == 1:
            sym.address = self.memory.alloc_global(size_bytes)
        else:
            sym.address = self.memory.alloc_local(size_bytes)
            
        current_scope[name] = sym
        return sym

    def lookup(self, name: str) -> Symbol:
        """從當前作用域往外層逐級查找符號 (變數查找)"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"未宣告的變數: '{name}'")