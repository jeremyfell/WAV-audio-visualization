# Import libraries
import sys
import os
import math
import tkinter as tk
import tkinter.filedialog
import tkinter.font

# Initial dimensions of the window
INITIAL_WIDTH = 1200
INITIAL_HEIGHT = 300

# Returns the file name to read
def get_file_name():
    return tk.filedialog.askopenfilename()

# Returns the max sample value and the min sample value
def get_samples_range(samples):
    max_value = float('-inf')
    min_value = float('inf')

    for sample in samples:
        # Keep track of max sample value found so far
        if sample > max_value:
            max_value = sample

        # Keep track of min sample value found so far
        if sample < min_value:
            min_value = sample

    return max_value, min_value

# Functions to compute the coefficients needed to fade each sample
def linear(x):
    return x

def quadratic(x):
    return x ** 2

def exponential(x):
    return math.pow(2, x) - 1

def logarithmic(x):
    return math.log(x + 1, 2)

# Fades the first 50% of samples in and fades the last 50% of samples out
# according to a parameter fade function
def fade_samples(samples, num_samples, sample_size, fade_function):
    if fade_function is None:
        return samples

    faded_samples = []
    half = num_samples // 2

    for i, sample in enumerate(samples):
        new_sample = sample

        # If 8-bit samples, adjust range to [-128,127] before fading
        if sample_size == 1:
            new_sample -= 128

        if i <= half:
            new_sample = math.floor(new_sample * fade_function(i / half))
        else:
            new_sample = math.floor(new_sample * fade_function((num_samples - i) / half))

        # If 8-bit samples, adjust range back to [0, 255]
        if sample_size == 1:
            new_sample += 128

        faded_samples.append(new_sample)

    return faded_samples

# Reads the .wav file
# Returns a list of samples and the number of samples
def read_wave_file(file_name):
    file = open(file_name, 'rb')

    # Check that the file is a WAVE file
    chunk_id = file.read(4).decode('ascii')  # Get ChunkID
    file.read(4) # Discard ChunkSize
    format = file.read(4).decode('ascii') # Get Format
    if chunk_id != 'RIFF' or format != 'WAVE':
        sys.exit('ERROR: {} is not a WAVE file'.format(file_name))

    file.read(4) # Discard Subchunk1ID

    # Check that the file is uncompressed
    subchunk_1_size = int.from_bytes(file.read(4), 'little') # Get Subchunk1Size
    audio_format = int.from_bytes(file.read(2), 'little') # Get AudioFormat
    if subchunk_1_size != 16 or audio_format != 1:
        sys.exit('ERROR: file must be uncompressed')

    # Check that the file is mono channel
    num_channels = int.from_bytes(file.read(2), 'little') # Get NumChannels
    if num_channels != 1:
        sys.exit('ERROR: file must be mono')

    file.read(4) # Discard SampleRate
    file.read(4) # Discard ByteRate
    file.read(2) # Discard BlockAlign

    bits_per_sample = int.from_bytes(file.read(2), 'little') # Get BitsPerSample

    file.read(4) # Discard Subchunk2ID
    subchunk_2_size = int.from_bytes(file.read(4), 'little') # Get Subchunk2Size

    sample_size = bits_per_sample // 8 # Compute size of sample in bytes
    num_samples = subchunk_2_size // sample_size # Compute number of samples
    signed = (sample_size > 1) # Whether to read samples as signed or unsigned (for 8-bit only)
    samples = []
    count = 0

    # Read all samples from the file
    while True:
        # Get the bytes for the next sample
        sample = file.read(sample_size)

        # Stop when end of file is reached
        if not sample:
            break

        # Convert sample bytes to the correct integer
        sample = int.from_bytes(sample, 'little', signed=signed)

        samples.append(sample)
        count += 1

    # Check that the number of samples specified in the WAVE header is
    # equal to the actual number of samples in the file
    if count != num_samples:
        sys.exit('ERROR: file has an incorrect number of samples')

    file.close()
    return samples, num_samples, sample_size

# Uses a closure to return a function that will draw the waveform after resizing the window
# and a function that will cycle between the different types of fading
def create_waveform_functions(canvas, window, faded_samples_list, num_samples, faded_samples_ranges, file_name):
    current_waveform = 0

    # Cycles to the next type of fading and redraws the waveform
    def next_waveform():
        nonlocal current_waveform
        titles = ['no', 'linear', 'quadratic', 'exponential', 'logarithmic']
        current_waveform = (current_waveform + 1) % 5
        window.title(os.path.basename(file_name) + ' - ' + titles[current_waveform] + ' fading')
        draw_waveform(canvas.winfo_width(), canvas.winfo_height())

    # Redraws the waveform after resizing the window
    def draw_resized_waveform(event):
        draw_waveform(event.width, event.height)

    # Draws the waveform in the window
    def draw_waveform(window_width, window_height):
        nonlocal current_waveform
        samples = faded_samples_list[current_waveform]
        (max_value, min_value) = faded_samples_ranges[current_waveform]

        # Clear canvas of current waveform
        canvas.delete('all')

        # Get range between largest and smallest samples
        range = abs(max_value - min_value)

        # Get dimension ratios between the number of samples and the width of the window
        # and between the range of sample values and the height of the window
        width_ratio = num_samples / window_width
        height_ratio = range / window_height

        # Threshold is used to compute when a sample should be drawn in the window
        # so that the waveform can be scaled to fit the window
        threshold = 0

        # Holds the current and previous coordinates for drawing the waveform
        x = 0
        prev_x = 0
        prev_y = 0

        # Iterate through the samples and draw them
        for sample in samples:
            while threshold >= width_ratio:
                threshold -= width_ratio
                x += 1

            # Computes the scaled y value for drawing the sample
            y = math.floor((sample - min_value) / height_ratio)

            # Draw line from previous coordinates to new computed coordinates
            canvas.create_line(prev_x, prev_y, x, y, fill='#0000ff')

            # New coordinates become the old coordinates
            prev_x = x
            prev_y = y

            threshold += 1

    return (next_waveform, draw_resized_waveform)

# The initial function called for the program
def main():
    # Create window and a canvas for the waveform
    window = tk.Tk()
    window.title('Loading...')
    canvas = tk.Canvas(window, width=INITIAL_WIDTH, height=INITIAL_HEIGHT, bg='white')

    # Get the file name and read the WAVE file
    file_name = get_file_name()
    (samples, num_samples, sample_size) = read_wave_file(file_name)
    (max_value, min_value) = get_samples_range(samples)
    fade_functions = [None, linear, quadratic, exponential, logarithmic]
    faded_samples_list = [fade_samples(samples, num_samples, sample_size, fade_function) for fade_function in fade_functions]
    faded_samples_ranges = [get_samples_range(faded_samples) for faded_samples in faded_samples_list]
    (faded_max_value, faded_min_value) = get_samples_range(samples)

    # Create labels for the number of samples, max value, and min value
    num_samples_text = tk.Label(text='Number of samples: ' + str(num_samples))
    max_value_text = tk.Label(text='Max value: ' + str(max_value))
    min_value_text = tk.Label(text='Min value: ' + str(min_value))

    # Add the canvas and labels to the window
    canvas.pack(expand=1, fill=tk.BOTH)
    num_samples_text.pack()
    max_value_text.pack()
    min_value_text.pack()
    window.title(os.path.basename(file_name) + ' - no fading')

    # Allows the waveform to be redrawn whenever the window is resized
    (next_waveform, draw_resized_waveform) = create_waveform_functions(canvas, window, faded_samples_list, num_samples, faded_samples_ranges, file_name)
    canvas.bind('<Configure>', draw_resized_waveform)

    # Adds a next button to cycle through different types of fading
    next_button = tk.Button(window, width=12, height=1, text='Next fade type', command=next_waveform, font=tk.font.Font(size=18))
    next_button.pack()

    # Update the window to draw the initial waveform
    window.mainloop()

if __name__ == '__main__':
    main()
