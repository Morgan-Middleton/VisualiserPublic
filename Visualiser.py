import librosa 
import pygame
import numpy
import tkinter
import tkinter.filedialog
from google_images_search import GoogleImagesSearch
import pathlib
import os.path

#Install commands used to run this application (pip may need to update)
#py -m pip install -U librosa --user
#py -m pip install -U pygame --user
#py -m pip install -U Google-Images-Search --user
#py -m pip install -U tk --user
#py -m pip install -U windows-curses --user

def fileprompt():
    top = tkinter.Tk()
    top.withdraw()  # hide window
    file_name = tkinter.filedialog.askopenfilename(parent=top)
    top.destroy()
    return file_name

def imageSearch(searchterm):
    gis = GoogleImagesSearch(dev_key, CX)
    params = {
    'q': searchterm,
    'num': 1,
    'fileType': 'png',
    'safe': 'medium',
    }
    gis.search(search_params=params, path_to_dir=pathlib.Path(__file__).parent.resolve(), width=100, height=100, custom_image_name='my_image')

#Prompt for file selection and extract filename, use filename to google search for album cover
filename = fileprompt()
filenameTrimmed = filename.rsplit('/', 1)[-1]
filenameTrimmed = filenameTrimmed[:-4]
print(filenameTrimmed)
imageSearch(filenameTrimmed)

# Process the audiofile: y = frequency, sr = samplerate (approx 2000 per sec)
y, sr = librosa.load(filename)

# Run the default beat tracker
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
print((str)(tempo) + " beats per minute")

# Convert the beat events into timestamps
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
# Round down the timestamps to 3 decimal places (now accurate to millisecond), this is to simplify checks between system and audio timestamps
roundedBeat_Times = []
for c in beat_times:
    rounded_c = round (c, 3)
    roundedBeat_Times.append(rounded_c)
    #print(rounded_c)

global freqAndTime

    #from here

AmplitudeByFreqAndTime = numpy.abs(librosa.stft(y, hop_length=512, n_fft=2048*4))

spectrogram = librosa.amplitude_to_db(AmplitudeByFreqAndTime, ref=numpy.max)  # converting the matrix to decibel matrix

frequencies = librosa.core.fft_frequencies(n_fft=2048*4)  # getting an array of frequencies

# getting an array of times
times = librosa.core.frames_to_time(numpy.arange(spectrogram.shape[1]), sr, hop_length=512, n_fft=2048*4)

time_index_ratio = len(times)/times[len(times) - 1]

frequencies_index_ratio = len(frequencies)/frequencies[len(frequencies)-1]

def get_decibel(target_time, freq):
    return spectrogram[int(freq * frequencies_index_ratio)][int(target_time * time_index_ratio)]

    #to here, code above involves a fourier transformation (maths that i don't fully understand) mostly taken from the documentation and tutorials

def get_beat(target_time):
    # if (target_time in roundedBeat_Times):
    #     return True
    # else:
    #     return False
    # code below incorporates a 5 millisecond margin of error when checking if a beat happens at a certain time
    for beat in roundedBeat_Times:
        if ((beat - 0.005) < target_time < (beat + 0.005)):
            return True
    return False


class drumCircle:
    def __init__(self, x, y, baseAmplitude, color):

        self.x, self.y, self.baseAmplitude, self.color = x, y, baseAmplitude, color

        self.width = 0

        self.amplitude = baseAmplitude

    def update(self, change):
        self.amplitude = self.baseAmplitude + change

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.amplitude, self.width)

    #slowly decrease size of circle in between beats
    def decrement(self):
        if self.amplitude > 10:
            self.amplitude = self.amplitude - 0.05

class freqBar:
    def __init__(self, left, top, width, height, color, frequency):

        self.left, self.top, self.height, self.width, self.frequency = left, top, height, width, frequency

        self.color = color

    def update(self, decibelLevel, screenHeight):
        #an inactive frequency range defaults to decibel -80, so i minus the decibel level from 80 
        #to ensure that bars grow as decibel increases (rather than the other way around)
        decibelMin = 80
        if decibelLevel < 0:
            decibelLevel = decibelLevel*-1
        decibelLevel = decibelMin - decibelLevel
        if decibelLevel < 25:
            self.color = (186, 86, 131)
        elif decibelLevel < 50:
            self.color = (255, 0, 115)
        else:
            self.color = (255, 0, 0)
        #self.top = screenHeight - decibelLevel
        #code below allows bars to expand on both sides of a baseline (up and down)
        self.top = screenHeight - (screenHeight/10) - (decibelLevel/2)
        self.height = decibelLevel

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, pygame.Rect((self.left, self.top), (self.width, self.height)))

def handleGraphics(AmplitudeArray, SampleRate):
     
    # initialize the pygame module
    pygame.init()

    #attempting to fix error "pygame.error: video system not initialized", this didn't work
    pygame.mixer.init()

    pygame.display.set_caption("Music visualizer")
     
    # size and background
    height = 500
    width = 500
    screen = pygame.display.set_mode((height, width), pygame.RESIZABLE)
    screen.fill((255, 255, 255))
    pygame.display.update()

    # load and set buttons
    stopBTN = pygame.image.load("stopButton.png")
    stopBTNScaled = pygame.transform.scale(stopBTN, (30, 30)).convert_alpha()
    playBTN = pygame.image.load("playBTN.png")
    playBTNScaled = pygame.transform.scale(playBTN, (30, 30))
    paused = False

    # load album cover, handles common filetypes as image search wasnt restricting filetype properly
    imageNotFound = False
    if os.path.exists("my_image.png"):
        albumCover = pygame.image.load("my_image.png")
        albumCoverScaled = pygame.transform.scale(albumCover, (100, 100))
    elif os.path.exists("my_image.jpg"):
        albumCover = pygame.image.load("my_image.jpg")
        albumCoverScaled = pygame.transform.scale(albumCover, (100, 100))
    else:
        imageNotFound = True
        print("Image not found")
     
    #Play music file
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play(0)
    pausePoint = 0

    #Declare range of freqBars
    rangeOfBars = []
    left = 0
    #frequencies = numpy.arange(100, 8000, 100)
    #arange(min, max, increment) - this should perhaps be dynamic. can cause performance and graphical 
    #issues if increment is too small, or range is too large.
    frequencies = numpy.arange(100, 4000, 25)
    numOfBars = len(frequencies)
    for a in frequencies:
        rangeOfBars.append(freqBar(left, 1, width/numOfBars, 1, (255, 0, 0), a))
        left = left + width/numOfBars

    drum = drumCircle(height/2, width/2, 50, (29, 81, 163))

    # define a variable to control the main loop
    running = True

    # main loop
    while running:
        #clear previous screen
        screen.fill((255, 232, 173))
        #draw correct play or pause button, and album cover
        if paused:
            screen.blit(playBTNScaled, (width-(width/10), height/20))
        else:
            screen.blit(stopBTNScaled, (width-(width/10), height/20))

        if imageNotFound == False:
            screen.blit(albumCoverScaled, (0, 0))
        
        # set each bar to match strength of particular freq range then re-draw
        for b in rangeOfBars:
            b.update(get_decibel(pygame.mixer.music.get_pos()/1000.0, b.frequency), screen.get_height())
            b.draw(screen)

        #print(get_decibel(pygame.mixer.music.get_pos()/1000.0, 100))

        # grow circle on beat, else shrink
        if get_beat(pygame.mixer.music.get_pos()/1000.0):
            drum.update(50)
            #print(pygame.mixer.music.get_pos()/1000.0)
        else:
            drum.decrement()
        drum.draw(screen)

        mouse = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # change the value to False, to exit the main loop
                running = False
                pygame.quit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                #play and pause button functionality
                if (width-(width/10) <= mouse[0] <= width-(width/10)+30) and ((height/20) <= mouse[1] <= (height/20)+30):
                    if paused == False:
                        paused = True
                        pausePoint = pygame.mixer.music.get_pos()
                        pygame.mixer.music.pause()
                    else:
                        paused = False
                        pygame.mixer.music.play()
                        #play from point doesnt work with .wav file format

            if event.type == pygame.VIDEORESIZE:
                width, height = pygame.display.get_surface().get_size()
                drum.x = width/2
                drum.y = height/2
                num = 0
                for b in rangeOfBars:
                    b.width = width/numOfBars
                    b.left = b.width*num
                    num = num+1
    
        pygame.display.flip()

handleGraphics(y, sr)