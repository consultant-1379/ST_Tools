set title "Percentage"
set key outside 
set ylabel "Result Code (%)"
set xlabel "Time (s)"
plot "result_code_percentage.data" using 1:2 title "Success" with lines 2, "result_code_percentage.data" using 1:3 title "UnableToComply" with lines 7, "result_code_percentage.data" using 1:4 title "TooBusy" with lines 1, "result_code_percentage.data" using 1:5 title "Other" with lines 8
load "loop_forever.gnu"
