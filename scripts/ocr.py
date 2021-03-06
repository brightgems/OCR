import matplotlib.pyplot as plt
import numpy as np
import cv2
import copy
import os
import shutil

from pylab import imread, imshow, figure, show, subplot, plot, scatter
from scipy.cluster.vq import kmeans, vq


def delete_files(directory):
    """ Deletes all files and folders contained in the directory """
    for the_file in os.listdir(directory):
        file_path = os.path.join(directory, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            #elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception, e:
            print e


# crop the digit and save as binary files, then return the boxed digits in 28 by 28
def save_digit_to_binary_img_as_mnist(img, dim = 28, saveToFile = True, imgSize = None, boundingRectMinSize = 5):
    """ takes in an image/ image name, crops the digit and save as dim by dim images, 
        then returns the image with digits bounding boxes drawn on it and 
        a list contains all the corpped digits
    """
    croppedDigits = [] # empty list holds all the cropped images

    # if img is a image name, then read it
    if isinstance(img, str): 
        img = cv2.imread(img)
    if imgSize: img = resize(img, imgSize)    # resize img to get better crops
    imgToShow = copy.copy(img)
    # thresh = binary_filter(img)

    # blur = cv2.GaussianBlur(img,(5, 5), 0)   
    edge = cv2.Canny(img,100,100)
    # ret,thresh = cv2.threshold(edge,127,255,cv2.THRESH_OTSU)
    ret,thresh = cv2.threshold(edge,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    threshToShow = copy.copy(thresh)

    # gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    contours,hierarchy = cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    idx = 0 
    for cnt in contours:
        if cnt.shape[0] >= boundingRectMinSize:
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(imgToShow,(x,y),(x+w,y+h),(0,255,0),1)
            cv2.rectangle(threshToShow,(x,y),(x+w,y+h),(0,255,0),1)

            # crop out the image, threshold it and save as binary image
            crop_img = img[y: y + h, x: x + w]   # img[y: y + h, x: x + w]
            grayed_im  = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            # blur = cv2.GaussianBlur(grayed_im,(5, 5), 0)  
            ret,thresh = cv2.threshold(grayed_im, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # resize image to fit mnist dataset
            resized_img = resize(thresh, dim)
            # make the digit pure binary
            bin_img = make_binary(resized_img)
            # make the digit black
            black_digit = make_digit_black(bin_img)
            # add padding to make it dim by dim
            padded_img = padding(black_digit, dim)
            white_digit = flip_binary(padded_img)
            # add cropped digits to list
            croppedDigits.append(white_digit) 
            if saveToFile: cv2.imwrite('../pics/cropped/' + str(idx) + '.png', white_digit)
            idx += 1
    return imgToShow, threshToShow, croppedDigits


# crop the digit and save as binary files, then return the boxed digits
def save_digit_as_binary_original(img, imgSize, boundingRectMinSize):
    if isinstance(img, str): 
        img = cv2.imread(img)    
    img = resize(img, imgSize)    # resize img to get better crops
    imgToShow = copy.copy(img)
    thresh = binary_filter(img)
    contours,hierarchy = cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    idx = 0 
    for cnt in contours:
        if cnt.shape[0] >= boundingRectMinSize:
            idx += 1
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(imgToShow,(x,y),(x+w,y+h),(0,255,0),1)

            # crop out the image, threshold it and save as binary image
            crop_img = img[y: y + h, x: x + w]   # img[y: y + h, x: x + w]
            grayed_im  = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            # blur = cv2.GaussianBlur(grayed_im,(5, 5), 0)  
            ret,thresh = cv2.threshold(grayed_im, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            cv2.imwrite('../pics/cropped/' + str(idx) + '.png', thresh)
    return imgToShow


# returns the image with digits boxed
def crop_digit(imgName, boundingRectMinSize):
    img = cv2.imread(imgName)
    thresh = binary_filter(img)
    contours,hierarchy = cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    idx = 0 
    for cnt in contours:
        if cnt.shape[0] >= boundingRectMinSize:
            idx += 1
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),1)      # draw box on original image
    return img


def binary_filter(img):
    """ takes in a colored img and returns the binary threshold """
    blur = cv2.GaussianBlur(img,(5, 5), 0)  
    edge = cv2.Canny(blur, 50, 50)
    # ret,thresh = cv2.threshold(edge,127,255,cv2.THRESH_OTSU)
    # Otsu's thresholding after Gaussian filtering and Canny edge detection
    ret,thresh = cv2.threshold(edge,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    return thresh

def resize(img, size):
    """ resize the image to fit in the size x size matrix """
    if img.shape[1] > img.shape[0]:
        r = float(size) / img.shape[1]
        dim = (int(size), int(img.shape[0] * r))
    else:
        r = float(size) / img.shape[0]
        dim = (int(img.shape[1] * r), int(size))

    resized_img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    return resized_img


def make_digit_black(img):
    """ flip the binary image if necessary to make it match mnist criteria 
        we detect the color of the digits by suming up the color of the peripherals
        of the picture, if the peripherals is white then the background is white, then
        we know the digit is black....
    """
    peripherals = np.empty([0,])
    h = img.shape[0]
    w = img.shape[1]
    peripherals = np.r_[peripherals, img[0,:]]  #get the sides
    peripherals = np.r_[peripherals, img[h-1,:]] 
    peripherals = np.r_[peripherals, img[:,0]] 
    peripherals = np.r_[peripherals, img[:,w-1]] 
    # if the mean color of the phericals of the image is white, that means 
    # the background is white, needs to flip the background to black, digit to white
    if np.mean(peripherals) < 127.5:
        return flip_binary(img)
    else: 
        return img

def make_binary(img):
    """ make the image pure black and white """
    for (x,y), pixel in np.ndenumerate(img):
        if img[x,y] > 127.5:
            img[x,y] = 255
        else:
            img[x,y] = 0
    return img


def flip_binary(img):
    for (x,y), pixel in np.ndenumerate(img):
        if img[x,y] == 0:
            img[x,y] = 255
        elif img[x,y] == 255:
            img[x,y] = 0
        else:
            print "flip_binary(): this image is not binary"

    return img

def padding(img, size):
    """ add padding to the image to make it square """
    padded = np.empty([size,size])
    padded.fill(255)
    h = img.shape[0]
    w = img.shape[1]
    x = int(size/2 - w/2)
    y = int(size/2 - h/2)
    padded[y: y + h, x: x + w] = img

    return padded



# obsolete code


# K means on color filtering, it doesn't clear out the background very well
# produces thick edge that connects digits together causion confusion
def img_kmeans(imgFile, k):
    img = imread(imgFile)
    # reshaping the pixels matrix to read in for k means
    pixel = np.reshape(img, (img.shape[0] * img.shape[1], 3))

    # performing the clustering on shaped pixels
    centroids, _ = kmeans(pixel, k)      # centeroids contains the 2 representative color of the image

    # quantization of 2 for color
    qnt, _ = vq(pixel, centroids)

    # reshaping the result of the quantization, clustered contains the cluster numbers
    clustered = np.reshape(qnt, (img.shape[0], img.shape[1]))   
    clustered_color = centroids[clustered]   #color the clustered
    return clustered, clustered_color


# binary matrix to position is used to convert binary image to positional matrix of each 
# non white pixel, it is then used for k means to cluster the digits into groups
# It didn't go well because digits sometimes are connected so they are often clustered together
def binary_matrix_to_position(binMat):
    """ takes in n x n binary True False color matrix and output a 
        n*n x 1 position matrix represent the position of colored digits 
    """
    binPosMat = np.empty((0,2), int)
    # go through the clustered matrix and get the position of the pixel that's not white
    for (x,y), pixel in np.ndenumerate(binMat):
        pixelColor =  binMat[x,y]
        if pixelColor == False:
            binPos = np.empty((1,2), int)
            binPos[0,0] = x
            binPos[0,1] = y
            binPosMat = np.append(binPosMat, binPos, axis=0)

    # flip the matrix
    return binPosMat


def binary_matrix_to_position_num(binMat):
    """ takes in n x n binary True False color matrix and output a 
        n*n x 1 position matrix represent the position of colored digits 
    """
    binPosMat = np.empty((0,2), int)
    # go through the clustered matrix and get the position of the pixel that's not white
    for (x,y), pixel in np.ndenumerate(binMat):
        pixelColor =  binMat[x,y]
        if pixelColor > 0:
            binPos = np.empty((1,2), int)
            binPos[0,0] = x
            binPos[0,1] = y
            binPosMat = np.append(binPosMat, binPos, axis=0)

    # flip the matrix
    return binPosMat

def binary_matrix_to_position_2(clustered):
    """ we assume the first color pixel that's most upper left of the image is not the 
    color of the number, a quick fix 
    """
    not_digit_color = clustered[1,1]

    binPosMat = np.empty((0,2), int)
    # go through the clustered matrix and get the position of the pixel that represent a digit
    for (x,y), pixel in np.ndenumerate(clustered):
        pixelColor =  clustered[x,y]
        if pixelColor != not_digit_color:
            binPos = np.empty((1,2), int)
            binPos[0,0] = x
            binPos[0,1] = y
            binPosMat = np.append(binPosMat, binPos, axis=0)

    return binPosMat
        
