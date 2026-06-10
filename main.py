# main.py
import sys
from repl import REPL

def main() -> None:
    # 支援直接透過命令列參數執行 C 檔案
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

        env = REPL()
        # 批次模式：靜默載入，不輸出 [系統] 提示訊息
        import io as _io
        _null = _io.StringIO()
        _old, sys.stdout = sys.stdout, _null
        env.do_load(filepath)
        sys.stdout = _old

        if env.source_lines:
            env.do_run()

    else:
        # 未提供檔案，啟動互動式 REPL
        env = REPL()
        env.start()

if __name__ == "__main__":
    main()