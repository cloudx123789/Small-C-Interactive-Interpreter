# Small-C Interactive Interpreter

> 系統軟體（System Software）Spring 2026 期末專題

一個以 Python 3 實作的 **Small-C 語言互動式解譯器**，提供類似早期 BASIC 解譯器的操作環境。使用者可在命令提示符下逐行輸入 Small-C 程式碼並即時執行，也可透過內建指令載入完整原始碼檔案後一次執行。

---

## 目錄

- [功能特色](#功能特色)
- [系統架構](#系統架構)
- [專案結構](#專案結構)
- [安裝與執行](#安裝與執行)
- [Small-C 語言規範](#small-c-語言規範)
- [REPL 環境指令](#repl-環境指令)
- [使用範例](#使用範例)
- [測試程式集](#測試程式集)
- [評分項目對照](#評分項目對照)

---

## 功能特色

| 類別 | 支援內容 |
|---|---|
| **資料型別** | `int`、`char`、`int*`、`char*`、一維陣列 |
| **運算子** | 算術、關係、邏輯（短路求值）、位元、複合指定（13 種）|
| **控制結構** | `if/else if/else`、`while`、`for`、`do/while`、`break`、`continue`、`return` |
| **函式** | 使用者定義函式、`void` 函式、遞迴、傳值呼叫、指標參數 |
| **內建函式** | 31 個（I/O、字串、數學、記憶體工具） |
| **前處理器** | `#define` 常數替換 |
| **互動環境** | 即時執行、多行輸入偵測、程式緩衝區管理 |
| **加分項目** | `switch/case`、執行期錯誤偵測（除零/越界/空指標）、`#define` |

---

## 系統架構

```
使用者輸入
    │
    ▼
┌─────────────────────────────────────────────────┐
│                    REPL (repl.py)               │
│  互動式命令解析 / 程式緩衝區管理 / 環境指令處理   │
└──────────────┬──────────────────────────────────┘
               │  原始碼字串
               ▼
┌──────────────────────────┐
│   前處理器 preprocess()  │  #define 展開
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│     Lexer (lexer.py)     │  字元流 → Token 序列
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│    Parser (parser.py)    │  Token → AST
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Interpreter (interpret.. │  AST → 執行結果
│  + SymbolTable           │
│  + MemoryManager         │
│  + BuiltinsFunctions     │
└──────────────────────────┘
```

### 模組說明

| 模組 | 職責 |
|---|---|
| `lexer.py` | 詞法分析，將原始碼轉換為 Token 序列；支援十六進位、跳脫序列、單/多行註解 |
| `parser.py` | 語法分析，遞迴下降解析器，建構 AST；含 `#define` 前處理 |
| `interpreter.py` | AST 直譯執行，Visitor 模式走訪節點 |
| `symtable.py` | 符號表管理，作用域堆疊（全域 / 區域），支援變數遮蔽 |
| `memory.py` | 記憶體管理器，模擬位元組陣列；含邊界檢查、NULL 防護 |
| `cbuiltins.py` | 31 個內建函式橋接 |
| `repl.py` | 互動式環境，程式緩衝區管理，所有環境指令 |
| `main.py` | 入口，支援互動模式與批次執行（`python main.py file.sc`）|

---

## 專案結構

```
.
├── main.py               # 程式入口
├── lexer.py              # 詞法分析器
├── parser.py             # 語法分析器（含前處理器）
├── interpreter.py        # 直譯執行引擎
├── symtable.py           # 符號表
├── memory.py             # 記憶體管理器
├── cbuiltins.py          # 內建函式庫
├── repl.py               # 互動式環境
├── README.md
│
├── tests/                # 測試程式集（13 組）
│   ├── test01_arithmetic.sc / .expected
│   ├── test02_variables.sc / .expected
│   ├── test03_control_if.sc / .expected
│   ├── test04_loops.sc / .expected
│   ├── test05_functions.sc / .expected
│   ├── test06_recursion.sc / .expected
│   ├── test07_arrays.sc / .expected
│   ├── test08_pointers.sc / .expected
│   ├── test09_strings.sc / .expected
│   ├── test10_define_bitwise.sc / .expected
│   ├── test11_syntax_error.sc / .expected
│   ├── test12_runtime_error.sc / .expected
│   └── test13_runtime_error2.sc / .expected
│
├── run_tests.py          # 批次自動測試腳本
```

---

## 安裝與執行

### 需求

- Python 3.10 以上
- 無需任何第三方套件

### 啟動互動式 REPL

```bash
python main.py
```

啟動後會顯示歡迎畫面並進入 `sc>` 提示符。

### 批次執行 .sc 檔案

```bash
python main.py program.sc
```

### 執行自動測試

```bash
python run_tests.py
```

---

## Small-C 語言規範

### 資料型別

```c
int x;              // 32 位元有號整數
int y = 10;
char ch = 'A';      // 8 位元有號字元
int arr[20];        // 一維整數陣列
char str[80];       // 字元陣列（字串）
int *ptr;           // 整數指標
char *cp;           // 字元指標
```

### 運算子優先順序（高 → 低）

| 級 | 運算子 |
|---|---|
| 1（最高）| `()` `[]` 函式呼叫 |
| 2 | 前綴 `-` `!` `~` `*` `&` `++` `--`（右結合）|
| 3 | `*` `/` `%` |
| 4 | `+` `-` |
| 5 | `<<` `>>` |
| 6 | `<` `<=` `>` `>=` |
| 7 | `==` `!=` |
| 8 | `&` |
| 9 | `^` |
| 10 | `\|` |
| 11 | `&&`（短路）|
| 12 | `\|\|`（短路）|
| 13（最低）| `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=`（右結合）|

### 控制結構

```c
// if / else if / else
if (x > 0) { ... }
else if (x == 0) { ... }
else { ... }

// while
while (i <= 100) { sum += i; i = i + 1; }

// for
for (i = 0; i < n; i = i + 1) { ... }

// do-while
do { printf("%d ", n); n = n + 1; } while (n <= 10);

// switch / case
switch (x) {
    case 1: printf("one\n"); break;
    case 2: printf("two\n"); break;
    default: printf("other\n");
}

// break / continue
for (i = 1; i <= 20; i = i + 1) {
    if (i % 3 == 0) continue;
    if (i > 15) break;
    printf("%d ", i);
}
```

### 函式

```c
int add(int a, int b) { return a + b; }

void swap(int *a, int *b) {
    int tmp;
    tmp = *a; *a = *b; *b = tmp;
}

int main() {
    printf("%d\n", add(3, 4));
    return 0;
}
```

### 前處理器

```c
#define MAX_SIZE 100
#define PI_APPROX 3

int arr[MAX_SIZE];
printf("PI ≈ %d\n", PI_APPROX);
```

### 內建函式（31 個）

**I/O**
```c
void printf(char *fmt, ...)   // 支援 %d %c %s %x %%
int  scanf(char *fmt, ...)
int  putchar(int ch)
int  getchar()
void puts(char *s)
```

**字串**
```c
int  strlen(char *s)
void strcpy(char *dst, char *src)
int  strcmp(char *s1, char *s2)
void strcat(char *dst, char *src)
```

**數學**
```c
int abs(int x)
int max(int a, int b)
int min(int a, int b)
int pow(int base, int exp)
int sqrt(int x)
int mod(int a, int b)
int rand()
void srand(int seed)
int sin(int x) / cos(int x) / tan(int x)
```

**轉換與工具**
```c
int  atoi(char *s)
void itoa(int val, char *str)
int  isalpha(int c) / isdigit(int c)
void memset(char *ptr, int val, int n)
int  sizeof_int() / sizeof_char()
int  malloc(int size) / void free(int ptr)
int  time(int ptr)
void exit(int code)
```

---

## REPL 環境指令

所有指令不區分大小寫。

### 程式管理

| 指令 | 說明 |
|---|---|
| `LOAD <filename>` | 從檔案載入 Small-C 原始碼 |
| `SAVE <filename>` | 儲存程式緩衝區至檔案 |
| `LIST` | 列出完整程式碼（含行號）|
| `LIST <n>` | 列出第 n 行 |
| `LIST <n1>-<n2>` | 列出第 n1 到 n2 行 |
| `EDIT <n>` | 編輯第 n 行 |
| `DELETE <n>` | 刪除第 n 行 |
| `DELETE <n1>-<n2>` | 刪除第 n1 到 n2 行 |
| `INSERT <n>` | 在第 n 行前插入（輸入 `.` 結束）|
| `APPEND` | 在末尾追加程式碼（輸入 `.` 結束）|
| `NEW` | 清除所有內容並重置狀態 |

### 執行與除錯

| 指令 | 說明 |
|---|---|
| `RUN` | 執行程式緩衝區中的程式 |
| `CHECK` | 語法與語意檢查（不執行）|
| `TRACE ON` | 開啟追蹤模式，每行顯示 `[line n] <statement>` |
| `TRACE OFF` | 關閉追蹤模式 |
| `VARS` | 顯示所有全域變數名稱、型別與當前值 |
| `FUNCS` | 列出所有函式（含內建函式標示 `[built-in]`）|

### 系統指令

| 指令 | 說明 |
|---|---|
| `HELP` | 顯示指令說明 |
| `ABOUT` | 顯示解譯器資訊 |
| `CLEAR` | 清除終端機畫面 |
| `QUIT` / `EXIT` | 離開解譯器 |

---

## 使用範例

### 互動模式即時執行

```
sc> printf("%d\n", 3 + 4 * 5 - 2);
21
sc> int x = 25;
sc> printf("sqrt(%d) = %d\n", x, sqrt(x));
sqrt(25) = 5
sc> char ch = 'Z';
sc> printf("ch=%c, ASCII=%d\n", ch, ch);
ch=Z, ASCII=90
```

### 多行程式輸入（APPEND）

```
sc> APPEND
   1> int factorial(int n) {
   2>     if (n <= 1) return 1;
   3>     return n * factorial(n - 1);
   4> }
   5> int main() {
   6>     int i;
   7>     for (i = 0; i <= 7; i = i + 1)
   8>         printf("%d! = %d\n", i, factorial(i));
   9>     return 0;
  10> }
  11> .
sc> RUN
0! = 1
1! = 1
2! = 2
3! = 6
4! = 24
5! = 120
6! = 720
7! = 5040
Program exited with return value 0.
```

### 錯誤偵測

```
sc> printf("%d\n", 10 / 0);
Runtime error: division by zero

sc> int arr[3];
sc> arr[5] = 10;
Runtime error: array index out of bounds (index 5, size 3)

sc> int bad = ;
Syntax error: line 1: unexpected token ';', expected expression
```

### TRACE 除錯模式

```
sc> TRACE ON
Trace mode enabled.
sc> RUN
[line 5] int result;
[line 6] result = gcd(48, 18);
  [line 2] while (...) { ... }
  [line 3] int temp;
  ...
GCD(48, 18) = 6
Program exited with return value 0.
sc> TRACE OFF
Trace mode disabled.
```

---

## 測試程式集

### 測試說明（`tests/`，13 組）

| 測試 | 涵蓋語言特性 |
|---|---|
| `test01_arithmetic` | 算術運算子優先順序、整除截斷（`-15/4=-3`）、十六進位 |
| `test02_variables` | 變數宣告、複合指定（`+=` `-=` `*=` `/=` `%=`）、char |
| `test03_control_if` | `if/else if/else`、邏輯運算 |
| `test04_loops` | `while`/`for`/`do-while`/`break`/`continue` |
| `test05_functions` | 多函式定義、`void` 函式 |
| `test06_recursion` | 階乘、GCD、次方遞迴 |
| `test07_arrays` | 陣列宣告、索引讀寫、傳入函式 |
| `test08_pointers` | `&` 取址、`*` 取值、透過指標修改 |
| `test09_strings` | 字串函式、數學函式全套 |
| `test10_define_bitwise` | `#define`、位元運算、`switch/case` |
| `test11_syntax_error` | 語法錯誤偵測 |
| `test12_runtime_error` | 除以零執行期錯誤 |
| `test13_runtime_error2` | 陣列越界執行期錯誤 |

### 自動測試執行

```bash
python run_tests.py
```

---

## 評分項目對照

| 評分項目 | 配分 | 實作狀態 |
|---|---|---|
| 6.1 詞法分析（Token 辨識） | 10 | ✅ 完整支援所有 Token 類型 |
| 6.1 語法分析（解析） | 10 | ✅ 變數、表達式、控制結構、函式 |
| 6.1 語法錯誤訊息 | 5 | ✅ 英文 `Error at line N: expected X, got Y` |
| 6.2 變數管理與作用域 | 6 | ✅ 全域/區域、作用域堆疊 |
| 6.2 算術/關係/邏輯/位元運算 | 6 | ✅ 含短路求值、C 截斷除法 |
| 6.2 控制結構 | 6 | ✅ 含 `break`/`continue`/`do-while` |
| 6.2 函式呼叫與遞迴 | 6 | ✅ 含指標參數傳遞 |
| 6.2 陣列與指標操作 | 6 | ✅ 含陣列退化、指標算術 |
| 6.3 REPL 基本運作 | 5 | ✅ 即時執行、多行輸入、持久狀態 |
| 6.3 程式管理指令 | 8 | ✅ LOAD/SAVE/LIST/EDIT/DELETE/INSERT/APPEND/NEW |
| 6.3 執行除錯指令 | 5 | ✅ RUN/CHECK/TRACE/VARS/FUNCS |
| 6.3 系統指令 | 2 | ✅ HELP/ABOUT/CLEAR/QUIT |
| 6.4 程式品質 | 5 | ✅ 模組化、英文錯誤訊息、命名規範 |
| 6.4 測試程式集 | 5 | ✅ 32 組 .sc + .expected |
| 6.4 專題報告 | 5 | — |
| **6.5 switch/case（加分）** | 5 | ✅ |
| **6.5 執行期錯誤完善處理（加分）** | 5 | ✅ 除零、越界（含 index/size）、空指標、sqrt 負數 |
| **6.5 #define（加分）** | 5 | ✅ 詞彙邊界替換 |

---

## 設計說明

### 記憶體模型

```
位址 0        : NULL（保留）
位址 4~1023   : Data Segment（全域變數）
位址 1024~    : Stack Segment（區域變數，依呼叫堆疊生長）
```

### 符號表設計

採用**作用域堆疊（Scope Stack）**：
- 索引 0 為全域作用域（Global Scope）
- 每次進入函式/區塊呼叫 `enter_scope()`，離開時呼叫 `leave_scope()` 並自動回收記憶體
- 變數查找從內層往外層逐級查找，實現變數遮蔽（Shadowing）

### 字串常數池化

字串字面值（`"hello"`）採用 **String Pool** 設計：
- 相同字串只在 Data Segment 配置一次
- 透過 `string_pool: Dict[str, int]` 字典記錄位址

### #define 實作

以正規表達式的詞彙邊界（`\b`）進行替換，確保 `MAX_SIZE` 不會誤替換 `MAX_SIZE_BUFFER` 中的子字串。