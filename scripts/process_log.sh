#!/bin/bash


# Check if input log file is provided
if [ -z "$1" ]; then
    echo "Error: No log file provided."
    exit 1
fi

# Log file and output CSV
log_file="$1"
output_csv="$2"

# Check if log file exists
if [ ! -f "$log_file" ]; then
    echo "Error: Log file does not exist."
    exit 1
fi

# Header for CSV
echo "LineId,timestamp,level,eventid,Template,Sentence" > "$output_csv"

awk '
BEGIN {
	FS="] "

}
{
	# Example: Extract Date (1st field), Level (2nd field), and Event Code (3rd field)
	if ($4)
        print $1 "," $2 "," "[" $3 " " $4
    else 
        print $1 "," $2 "," "[" $3

}' "$log_file" >> output_dumy.csv
sed 's/\[\([A-Za-z ]\)/\1/g; s/\(\[client [0-9]*\.[0-9]*\.[0-9]*\.[0-9]*\)/\1]/g;' output_dumy.csv > dumy.csv && mv dumy.csv output_dumy.csv
sed 's/\([A-Za-z0-9:]*\),\([a-z]*\),\([^ ]*\)/\1,\2,\3 <*>,\3/g' output_dumy.csv > dumy.csv && mv dumy.csv output_dumy.csv
awk '
BEGIN {
        FS=","
}
{   
    sentence = $4

    if (sentence ~ /jk2_init\(\) Found child [0-9]+ in scoreboard slot [0-9]+/) 
        {
        event_code = "E1"
        template = "k2_init() Found child <*> in scoreboard slot <*>"
        }
    else if (sentence ~ /workerEnv\.init\(\) ok .*/)
        {
        event_code = "E2"
        template = "workerEnv.init() ok <*>"
        }
    else if (sentence ~ /mod\_jk child workerEnv in error state [0-9]/)
        {
        event_code = "E3"
        template = "mod_jk child workerEnv in error state <*>"
        }
    else if (sentence ~ /\[client [0-9]*\.[0-9]*\.[0-9]*.[0-9]*\] Directory index forbidden by rule\: .*/)
        {
        event_code = "E4"
        template = "[client <*>] Directory index forbidden by rule: <*>"
        }
    else if (sentence ~ /jk2_init\(\) Can'\''t find child [0-9]+ in scoreboard/)
        {
        event_code = "E5"
        template = "jk2_init() Can'\''t find child <*> in scoreboard"
        }
    else if (sentence ~ /mod\_jk child init [0-9]* [0-9]*/)
        {
        event_code = "E6"
        template = "mod_jk child init <*>"
        }
    else
        event_code = ""

    print NR "," $1 "," $2 "," event_code "," template "," $4
    # Example: Extract Date (1st field), Level (2nd field), and Event Code (3rd field)
    
}' output_dumy.csv >> "$output_csv"

rm output_dumy.csv
echo "Log processing complete. CSV saved as $output_csv"

