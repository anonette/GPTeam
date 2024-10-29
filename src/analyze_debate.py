import sys
from pathlib import Path
from src.web.discussion_tracker import analyze_debate
from src.web.debate_report import create_debate_report

def main() -> None:
    """
    Analyze the AI debate logs and display insights via Streamlit.
    Usage: streamlit run analyze_debate.py
    """
    agents_dir = Path('agents')
    if not agents_dir.exists():
        print("Error: agents directory not found")
        sys.exit(1)
        
    # Get all .txt files in the agents directory
    log_files = list(agents_dir.glob('*.txt'))
    if not log_files:
        print("Error: No log files found in agents directory")
        sys.exit(1)
        
    # Analyze each agent's log
    for log_file in log_files:
        print(f"Analyzing log: {log_file}")
        try:
            create_debate_report(str(log_file))
        except Exception as e:
            print(f"Error analyzing {log_file}: {str(e)}")
            continue

if __name__ == "__main__":
    main()
