# Debate Analysis System

A comprehensive system for analyzing and visualizing multi-agent debate logs, providing insights into argument effectiveness, participant dynamics, and debate evolution.

## Features

### 1. Debate Dynamics Analysis
- **Position Shift Tracking**: Identifies when and why participants change their stances
- **Argument Impact**: Measures effectiveness of arguments by tracking responses
- **Influence Analysis**: Evaluates each participant's impact on the debate
- **Consensus Tracking**: Identifies moments of agreement and disagreement

### 2. Participant Analysis
- **Participation Statistics**: 
  - Message count and frequency
  - Broadcast vs. direct conversation patterns
  - Interaction preferences
- **Strategy Profiling**:
  - Primary debate approaches (Emotional, Confrontational, Persuasive)
  - Argument pattern analysis
  - Tactical adaptations

### 3. Content Analysis
- **Quote Categorization**:
  - Emotional Appeals
  - Calls to Action
  - Key Arguments
  - Notable Confrontations
- **Argument Classification**:
  - Tracks emotional vs. logical arguments
  - Identifies persuasive techniques
  - Analyzes rhetorical strategies

### 4. Visual Presentation
- Interactive expandable sections
- Progress bars for interaction patterns
- Card-based layout for key insights
- Color-coded argument categorization
- Tabbed organization for different quote types

## Usage

1. **Starting the Analysis System**:
   ```bash
   streamlit run src/web/debate_report.py
   ```

2. **Selecting a Debate Log**:
   - Choose from available debate logs in the dropdown menu
   - Logs should be located in `src/web/logs/archive/`

3. **Navigating the Report**:
   - Use the expandable sections to explore different aspects of the analysis
   - Click through tabs to view different categories of quotes
   - Hover over metrics for additional information

## Log Format Requirements

The system expects debate logs to contain:
- Timestamped messages
- Speaker identification
- Message content
- Action/reaction markers
- JSON-formatted message data

Example log entry:
```
[2024-10-28T20:07:21.289593]Speaker: Action Input: {
    "recipient": "everyone",
    "message": "Example debate message"
}
```

## Key Insights Provided

1. **Debate Evolution**:
   - How positions change over time
   - Which arguments are most influential
   - When and why stance shifts occur

2. **Participant Dynamics**:
   - Who drives the conversation
   - How participants interact
   - Different debate strategies employed

3. **Argument Effectiveness**:
   - Which types of arguments generate responses
   - How emotional vs. logical appeals perform
   - What leads to position shifts

4. **Pattern Recognition**:
   - Common debate strategies
   - Interaction preferences
   - Rhetorical techniques

## Technical Details

The system consists of two main components:

1. **discussion_tracker.py**:
   - Handles log parsing and analysis
   - Implements debate dynamics tracking
   - Performs statistical analysis

2. **debate_report.py**:
   - Creates the visual interface
   - Manages user interaction
   - Presents analysis results

## Dependencies

- Streamlit (for visualization)
- Python 3.10+
- Standard Python libraries:
  - re (for pattern matching)
  - json (for message parsing)
  - datetime (for timestamp handling)
  - pathlib (for file operations)
  - collections (for data organization)

## Future Enhancements

Planned improvements include:
- Real-time analysis capabilities
- Advanced sentiment analysis
- Network graph visualizations
- Comparative debate analysis
- Custom metric definitions
- Export functionality for analysis results

## Contributing

To contribute to the debate analysis system:
1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Submit a pull request

Please ensure all changes maintain or enhance the current analysis capabilities.
