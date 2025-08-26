#!/bin/bash

# Script to run the diligence agent with full monitoring and output capture

echo "============================================"
echo "Starting Diligence Agent with Full Monitoring"
echo "============================================"
echo ""

# Create output directory with timestamp in the output folder
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="output/monitor_${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

echo "📁 Output directory: $OUTPUT_DIR"
echo ""

# Function to display real-time progress
monitor_progress() {
    echo "🔍 Monitoring agent progress..."
    echo ""
}

# Run the crew and capture all output
echo "🚀 Starting crew execution..."
echo "================================"

# Run with full output capture
uv run crewai run 2>&1 | tee "$OUTPUT_DIR/full_output.log" | while IFS= read -r line; do
    # Color code different types of output
    if [[ $line == *"Data Validator"* ]]; then
        echo -e "\033[34m[VALIDATION] $line\033[0m"  # Blue for validation
    elif [[ $line == *"verified_facts"* ]] || [[ $line == *"completeness_score"* ]]; then
        echo -e "\033[32m[VERIFIED] $line\033[0m"  # Green for verified data
    elif [[ $line == *"red_flags"* ]] || [[ $line == *"unverified"* ]]; then
        echo -e "\033[31m[WARNING] $line\033[0m"  # Red for warnings
    elif [[ $line == *"Final Answer"* ]]; then
        echo -e "\033[35m[RESULT] $line\033[0m"  # Magenta for results
    elif [[ $line == *"Task Completed"* ]]; then
        echo -e "\033[36m[COMPLETE] $line\033[0m"  # Cyan for completion
    elif [[ $line == *"Search the internet"* ]]; then
        echo -e "\033[33m[SEARCH] $line\033[0m"  # Yellow for searches
    else
        echo "$line"
    fi
done

echo ""
echo "================================"
echo "✅ Crew execution completed!"
echo ""

# Extract key sections from the log
echo "📊 Extracting key insights..."

# Extract validation report
echo "Extracting validation report..." 
grep -A 50 "data_validation" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/validation_report.json" 2>/dev/null

# Extract each section
grep -A 100 "Overview of Tensorstax" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/overview_section.md" 2>/dev/null
grep -A 100 "Why.*Interesting" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/why_interesting_section.md" 2>/dev/null
grep -A 100 "Product Section" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/product_section.md" 2>/dev/null
grep -A 100 "Market.*Section" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/market_section.md" 2>/dev/null
grep -A 100 "Competitive.*Landscape" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/competitive_section.md" 2>/dev/null
grep -A 100 "Team.*Section" "$OUTPUT_DIR/full_output.log" > "$OUTPUT_DIR/team_section.md" 2>/dev/null

# Create summary report
echo "📝 Creating summary report..."
cat > "$OUTPUT_DIR/summary.txt" << EOF
DILIGENCE AGENT RUN SUMMARY
============================
Date: $(date)
Company: Tensorstax

Key Findings:
-------------
EOF

# Add validation score if found
if grep -q "completeness_score" "$OUTPUT_DIR/full_output.log"; then
    echo "✓ Data Validation Score: $(grep -o 'completeness_score.*[0-9]\+' "$OUTPUT_DIR/full_output.log" | head -1)" >> "$OUTPUT_DIR/summary.txt"
fi

# Count verified facts
VERIFIED_COUNT=$(grep -c "verified_facts" "$OUTPUT_DIR/full_output.log" 2>/dev/null || echo "0")
echo "✓ Verified Facts Found: $VERIFIED_COUNT" >> "$OUTPUT_DIR/summary.txt"

# Count web searches performed
SEARCH_COUNT=$(grep -c "Search the internet" "$OUTPUT_DIR/full_output.log" 2>/dev/null || echo "0")
echo "✓ Web Searches Performed: $SEARCH_COUNT" >> "$OUTPUT_DIR/summary.txt"

# Count completed tasks
TASK_COUNT=$(grep -c "Task Completed" "$OUTPUT_DIR/full_output.log" 2>/dev/null || echo "0")
echo "✓ Tasks Completed: $TASK_COUNT" >> "$OUTPUT_DIR/summary.txt"

echo "" >> "$OUTPUT_DIR/summary.txt"
echo "Output Files Generated:" >> "$OUTPUT_DIR/summary.txt"
echo "----------------------" >> "$OUTPUT_DIR/summary.txt"
ls -la "$OUTPUT_DIR/" >> "$OUTPUT_DIR/summary.txt"

# Display summary
echo ""
echo "📈 RUN SUMMARY"
echo "=============="
cat "$OUTPUT_DIR/summary.txt"

echo ""
echo "📂 All output saved to: $OUTPUT_DIR/"
echo ""
echo "To view the full log:"
echo "  less $OUTPUT_DIR/full_output.log"
echo ""
echo "To view specific sections:"
echo "  cat $OUTPUT_DIR/validation_report.json"
echo "  cat $OUTPUT_DIR/overview_section.md"
echo ""