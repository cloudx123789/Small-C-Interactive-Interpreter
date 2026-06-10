# memory.py
import struct
from typing import List, Tuple

class NullPointerError(RuntimeError):
    """空指標取值例外"""
    pass

class OutOfBoundsError(RuntimeError):
    """記憶體存取越界例外"""
    pass

class MemoryManager:
    """記憶體管理器：模擬真實位元組陣列，實作位址映射、指標取值與邊界檢查"""
    
    def __init__(self, size: int = 65536):
        self.size = size
        # 實體記憶體，全部初始化為 0
        self.ram = bytearray(size)
        
        # 記錄當前合法分配的記憶體區塊，格式為 (start_address, end_address)
        self.valid_blocks: List[Tuple[int, int]] = []
        
        # 位址 0 保留為 NULL，Data Segment (全域) 從 4 開始向上生長
        self.global_sp = 4 
        
        # Stack Segment (區域) 從 1024 開始向上生長 (模擬堆疊幀)
        self.stack_sp = 1024 

    def _register_block(self, addr: int, size_bytes: int) -> None:
        """註冊合法區塊，用於執行期越界檢查"""
        if size_bytes > 0:
            self.valid_blocks.append((addr, addr + size_bytes - 1))

    def alloc_global(self, size_bytes: int) -> int:
        """配置全域記憶體"""
        addr = self.global_sp
        self.global_sp += size_bytes
        if self.global_sp >= 1024:
            raise MemoryError("全域記憶體區段溢位 (Data Segment Overflow)")
        self._register_block(addr, size_bytes)
        return addr

    def alloc_local(self, size_bytes: int) -> int:
        """配置區域記憶體 (堆疊)"""
        addr = self.stack_sp
        self.stack_sp += size_bytes
        if self.stack_sp >= self.size:
            raise MemoryError("堆疊溢位 (Stack Overflow)")
        self._register_block(addr, size_bytes)
        return addr

    def free_locals(self, restore_sp: int) -> None:
        """釋放區域記憶體：清除大於等於 restore_sp 的合法區塊並恢復指標"""
        self.valid_blocks = [
            (start, end) for start, end in self.valid_blocks if start < restore_sp
        ]
        self.stack_sp = restore_sp

    def check_access(self, addr: int, size: int) -> None:
        """核心防護：檢查目標位址區間是否完全落於合法的記憶體區塊內"""
        if addr == 0:
            raise NullPointerError("嘗試存取空指標 (Null Pointer Dereference)")
            
        end_addr = addr + size - 1
        for start, end in self.valid_blocks:
            if start <= addr and end_addr <= end:
                return # 存取合法
                
        raise OutOfBoundsError(f"記憶體存取越界 (Segmentation Fault): 試圖存取位址區間 {addr}~{end_addr}")

    # ==========================================
    # 資料存取介面 (處理 Endianness 與型別轉換)
    # ==========================================
    def write_int(self, addr: int, val: int) -> None:
        self.check_access(addr, 4)
        # 轉換為 32-bit signed integer (Little Endian)
        self.ram[addr:addr+4] = struct.pack('<i', val)

    def read_int(self, addr: int) -> int:
        self.check_access(addr, 4)
        return struct.unpack('<i', self.ram[addr:addr+4])[0]

    def write_char(self, addr: int, val: int) -> None:
        self.check_access(addr, 1)
        # 轉換為 8-bit signed char
        self.ram[addr:addr+1] = struct.pack('<b', val)

    def read_char(self, addr: int) -> int:
        self.check_access(addr, 1)
        return struct.unpack('<b', self.ram[addr:addr+1])[0]
        
    def write_pointer(self, addr: int, ptr_val: int) -> None:
        self.check_access(addr, 4)
        # 指標值我們以 unsigned 32-bit integer 儲存
        self.ram[addr:addr+4] = struct.pack('<I', ptr_val)

    def read_pointer(self, addr: int) -> int:
        self.check_access(addr, 4)
        return struct.unpack('<I', self.ram[addr:addr+4])[0]

#test
if __name__ == "__main__":
    import memory, symtable

    mem = memory.MemoryManager()
    sym = symtable.SymbolTable(mem)

    print("=== [記憶體與符號表單元測試] ===")
    
    # 1. 測試全域變數宣告與讀寫
    sym.declare("g_var", "int")
    g_sym = sym.lookup("g_var")
    mem.write_int(g_sym.address, 100)
    print(f"[OK] 全域變數 g_var 分配於位址 {g_sym.address}，值為 {mem.read_int(g_sym.address)}")

    # 2. 測試作用域與陣列配置
    sym.enter_scope()
    sym.declare("arr", "int", is_array=True, array_size=5) # 5 * 4 = 20 bytes
    arr_sym = sym.lookup("arr")
    
    # 寫入 arr[2] (偏移 2 * 4 = 8 bytes)
    offset_address = arr_sym.address + (2 * 4)
    mem.write_int(offset_address, 888)
    print(f"[OK] 陣列 arr[2] 分配於位址 {offset_address}，值為 {mem.read_int(offset_address)}")

    # 3. 測試陣列越界防護 (試圖存取 arr[5]，此為 out-of-bounds)
    print("\n--- 測試陣列越界防護 ---")
    try:
        invalid_address = arr_sym.address + (5 * 4)
        mem.read_int(invalid_address)
        print("[FAIL] 未攔截到越界")
    except memory.OutOfBoundsError as e:
        print(f"[OK] 成功攔截越界存取: {e}")

    # 4. 測試空指標防護
    print("\n--- 測試空指標防護 ---")
    try:
        mem.write_int(0x0000, 999)
        print("[FAIL] 未攔截到空指標")
    except memory.NullPointerError as e:
        print(f"[OK] 成功攔截空指標存取: {e}")

    # 5. 測試記憶體回收 (離開作用域)
    print("\n--- 測試區域記憶體回收 ---")
    sym.leave_scope()
    
    # 此時 arr 已經失效，其記憶體區段應被回收
    try:
        mem.read_int(arr_sym.address)
        print("[FAIL] 未攔截到失效的記憶體存取 (Use-after-free 未被釋放)")
    except memory.OutOfBoundsError as e:
        print(f"[OK] 區域記憶體已成功回收 (攔截到野指標存取): {e}")

    print("\n=> 第三階段 (第一部分)：記憶體與符號表測試全數通過。")