# How to use Tracker 
1. Run the python file run.py to start
2. Click file on header and open your MP4 video 
3. Calibrate using known points. I suggest around bottom most red number ~ 11 cm
4. Save calibration preset on header, so you don't have to do it again (optional)
5. Enable autoclicker. I suggest setting it to 3, 5, 7 CPS (Recommended)
6. Click away and measure points
7. Export to CSV 

## Important Note
The columns option in the header is for offsetting the data. There is a column called "correct y"
that adds 10 cm to the measured y value that is configured for my calibration points. I set my origin to 10 cm IRL height, 
so I add 10 cm to get the real height. 

# How to use Wave Aligner 
1. Run the python file run.py to start
2. Shift graphs to your desired positions. Minimize NRMSE 
3. Export graph 

## Edit axises
Use the edit axises button to name your graph (also names your exported png) and set range. 

## Export shifts 
This feature takes your current graphs and time shifts and creates new CSV files to match the graph. 
Made for making original data match the graphs since we want our graphs to start at 0 and you cut data
points below t = 0 when shifting. 