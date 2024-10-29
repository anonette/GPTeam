import streamlit as st
from pathlib import Path
from src.web.discussion_tracker import analyze_debate

def create_debate_report(log_file: str) -> None:
    """Create a debate report with summary, key quotes, and strategy analysis"""
    st.title(f"Analysis of {Path(log_file).stem}'s Debate Log")
    
    try:
        # Get analysis from discussion tracker
        analysis = analyze_debate(log_file)
        
        # Display summary in an expandable section
        with st.expander("📊 Summary and Key Insights", expanded=True):
            st.write(analysis['summary'])
        
        # Display debate dynamics
        st.header("🔄 Debate Evolution")
        dynamics = analysis['debate_dynamics']
        
        # Show influential arguments in a modern card-like format
        if dynamics['influential_arguments']:
            st.subheader("💡 Most Impactful Arguments")
            for arg in dynamics['influential_arguments'][:3]:
                with st.container():
                    st.markdown(f"""
                    <div style='padding: 10px; border-left: 3px solid #1f77b4;'>
                    <strong>Impact: {arg['response_count']} responses</strong><br>
                    {arg['argument']}
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("")  # Add spacing
        
        # Show stance changes in a timeline-like format
        if dynamics['stance_changes']:
            st.subheader("🔄 Key Position Shifts")
            for i, change in enumerate(dynamics['stance_changes'][:3], 1):
                with st.container():
                    st.markdown(f"""
                    <div style='padding: 10px; border-left: 3px solid #2ecc71;'>
                    <strong>Shift {i}: {change['speaker']}</strong><br>
                    {change['reason'].split('.')[0]}
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("")  # Add spacing
        
        # Display participation statistics in a modern grid
        st.header("👥 Participation Analysis")
        cols = st.columns(3)
        for i, (participant, stats) in enumerate(analysis['participation'].items()):
            with cols[i % 3]:
                st.markdown(f"### {participant}")
                st.metric("Messages", stats['count'])
                st.metric("Broadcasts", stats['broadcasts'])
                st.metric("Direct Conversations", stats['conversations'])
        
        # Display interaction patterns with visual hierarchy
        st.header("🔄 Interaction Dynamics")
        for speaker, targets in analysis['interactions'].items():
            with st.expander(f"{speaker}'s Interaction Pattern", expanded=True):
                for target, percentage in targets.items():
                    # Create a progress bar for interaction percentage
                    st.markdown(f"**{target}**")
                    st.progress(percentage / 100)
                    st.write(f"{percentage:.1f}% of interactions")
        
        # Display strategy analysis with improved visualization
        st.header("⚔️ Debate Strategies")
        for agent, strategy in analysis['strategies'].items():
            with st.expander(f"{agent}'s Strategy Profile", expanded=True):
                st.markdown(f"**Primary Approach:** {strategy['primary_strategy']}")
                
                # Display stats with visual indicators
                stats = strategy['stats']
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Emotional Appeals", stats['emotional_appeals'],
                            delta="High" if stats['emotional_appeals'] > 5 else "Low")
                with cols[1]:
                    st.metric("Confrontational", stats['confrontational_statements'],
                            delta="High" if stats['confrontational_statements'] > 5 else "Low")
                with cols[2]:
                    st.metric("Persuasive", stats['persuasive_arguments'],
                            delta="High" if stats['persuasive_arguments'] > 5 else "Low")
        
        # Display notable quotes in a more engaging format
        st.header("💬 Notable Quotes")
        
        # Create tabs for different quote categories
        quote_tabs = st.tabs(["Emotional Appeals", "Calls to Action", "Key Arguments", "Confrontations"])
        
        with quote_tabs[0]:
            for quote in analysis['categorized_quotes']['emotional_appeals'][:3]:
                st.markdown(f"""
                <div style='padding: 10px; border-left: 3px solid #e74c3c;'>
                {quote['message']}<br>
                <em>— {quote['speaker']}</em>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
        
        with quote_tabs[1]:
            for quote in analysis['categorized_quotes']['calls_to_action'][:3]:
                st.markdown(f"""
                <div style='padding: 10px; border-left: 3px solid #f39c12;'>
                {quote['message']}<br>
                <em>— {quote['speaker']}</em>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
        
        with quote_tabs[2]:
            for quote in analysis['categorized_quotes']['key_arguments'][:3]:
                st.markdown(f"""
                <div style='padding: 10px; border-left: 3px solid #3498db;'>
                {quote['message']}<br>
                <em>— {quote['speaker']}</em>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
        
        with quote_tabs[3]:
            for quote in analysis['categorized_quotes']['confrontations'][:3]:
                st.markdown(f"""
                <div style='padding: 10px; border-left: 3px solid #9b59b6;'>
                {quote['message']}<br>
                <em>— {quote['speaker']}</em>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
            
    except Exception as e:
        st.error(f"Error analyzing discussion: {str(e)}")
        st.exception(e)

def main():
    """Main function to run the Streamlit app"""
    st.set_page_config(
        page_title="Debate Analysis",
        page_icon="📊",
        layout="wide"
    )
    
    log_dir = Path("src/web/logs/archive")
    log_files = list(log_dir.glob("*.txt"))
    
    if not log_files:
        st.error("No debate log files found!")
        return
        
    # Let user select which agent's log to analyze
    selected_log = st.selectbox(
        "Select a debate log to analyze",
        options=log_files,
        format_func=lambda x: x.stem
    )
    
    create_debate_report(str(selected_log))

if __name__ == "__main__":
    main()
