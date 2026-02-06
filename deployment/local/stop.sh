#!/bin/bash

echo "Stopping all services started by start.sh..."

# Function to kill processes in terminal and close the terminal tab/window
kill_and_close_terminal_by_title() {
    local title=$1
    local service_name=$2
    
    echo "Looking for $service_name terminal with title: $title..."
    
    # Use osascript to find terminals with matching title, kill processes, and close them
    osascript <<EOF
tell application "Terminal"
    set windowCount to count of windows
    repeat with i from windowCount to 1 by -1
        set w to window i
        set tabCount to count of tabs of w
        repeat with j from tabCount to 1 by -1
            set t to tab j of w
            try
                if custom title of t contains "$title" then
                    -- Get the tty of this tab
                    set ttyName to tty of t
                    
                    -- Kill all processes in this terminal session
                    do shell script "pkill -9 -t " & ttyName
                    
                    -- Wait a moment for processes to die
                    delay 0.5
                    
                    -- Close the tab
                    do script "exit" in t
                    
                    log "Killed processes and closed terminal for $service_name"
                end if
            on error errMsg
                log "Error processing tab: " & errMsg
            end try
        end repeat
    end repeat
end tell
EOF
    
    echo "$service_name terminal processes killed and terminal closed."
}

# Kill and close terminals by their custom titles
echo "Stopping services by closing their terminal tabs..."
kill_and_close_terminal_by_title "AIIntegrator-Integrator" "integrator"
kill_and_close_terminal_by_title "AIIntegrator-SupportServices" "support_services"
kill_and_close_terminal_by_title "AIIntegrator-MCPServices" "mcp_services"
kill_and_close_terminal_by_title "AIIntegrator-Portal" "portal"

echo ""
echo "All services stopped and terminals closed."

exit 0
