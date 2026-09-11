"""Quick manual test runner demonstrating the FastMCP server tools end-to-end."""

import json
from server import save_code, run_code_and_show_plot, list_saved_analyses

SAMPLE_CODE = '''import yfinance as yf
import matplotlib.pyplot as plt

print("Downloading AAPL 1-month market data...")
data = yf.download("AAPL", period="1mo", progress=False)

plt.figure(figsize=(10, 5))
plt.plot(data["Close"], label="AAPL Close", color="#0066cc", linewidth=2)
plt.title("AAPL - 1 Month Close Price", fontsize=14, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Price (USD)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig("outputs/AAPL_1mo_sample.png", bbox_inches="tight")
print("Chart saved successfully to outputs/AAPL_1mo_sample.png")
'''

def main():
    print("\n--- 1. Testing save_code() tool with AST validation ---")
    save_resp = save_code(SAMPLE_CODE, filename="AAPL_1mo_sample.py")
    print(save_resp)

    print("\n--- 2. Testing run_code_and_show_plot() in isolated subprocess ---")
    exec_resp = run_code_and_show_plot("outputs/AAPL_1mo_sample.py")
    print(exec_resp)

    print("\n--- 3. Testing list_saved_analyses() tool ---")
    list_resp = list_saved_analyses()
    print(list_resp)

if __name__ == "__main__":
    main()
