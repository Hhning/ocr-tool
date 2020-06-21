"""
This file contains functions that wraps tesserocr to convert an image that contains digits to a string.

Required libraries:
  - tesserocr: https://pypi.python.org/pypi/tesserocr
  - Python Imaging Library (PIL)
  - scikit-image
  - numpy
"""


import subprocess
import os
import numpy
import warnings
import skimage
import PIL
import cv2
from skimage import io
from skimage import filters

import pytesseract

# For debug purposes only
DEBUG_OUTPUT_TMP_IMG_FLAG = False

# For debug purposes only, switch this to true
DEBUG_OUTPUT_TMP_STEP_IMAGES_FLAG = False

# height ratio threshold to remove leading colon
HEIGHT_RATIO = 0.65

# some const variable
LARGE_NUMBER = 10000000000
SMALL_NUMBER = -1
EXPAND_PIXEL_NUMBER = 2
FIXED_HEIGHT = 50
PAD_WIDTH_RATIO = 0.1
PAD_HEIGHT_RATIO = 0.3
REMOVE_BORDER_LINE_RATIO = 0.6




# -------------------------- PUBLIC FUNCTIONS ---------------------------------


def imagefile_to_digit_string(filename, whitelistchars="0123456789", removeboundingbox=True):
    """Converts an image file that contains digits to a string.

    Args:
        filename: Path to the image file (PNG or JPG)
        whitelistchars (Optional): String of letters to be recognized by the OCR
                                   By default, it is set to only recognize digits.
                                   Change this value if you want OCR to recognize different symbols/letters,
                                   but having too many characters here can drop the accuracy.
        removeboundingbox (Optional): If True, it will automatically detect and remove bounding boxes from the image.
                                      If accuracy is very low, try switching this to false.

    Returns:
        String of digits converted from the image file.
    """
    skimg = skimage.io.imread(filename) # Read image file as skimage
    return skimage_to_digit_string(skimg, whitelistchars, removeboundingbox, filename)

def PILimage_to_digit_string(img, whitelistchars="0123456789", removeboundingbox=True):
    """Converts a PIL image that contains digits to a string.

    Args:
        img: PIL image in RGB mode
        whitelistchars (Optional): String of letters to be recognized by the OCR
                                   By default, it is set to only recognize digits.
                                   Change this value if you want OCR to recognize different symbols/letters,
                                   but having too many characters here can drop the accuracy.
        removeboundingbox (Optional): If True, it will automatically detect and remove bounding boxes from the image.
                                      If accuracy is very low, try switching this to false.

    Returns:
        String of digits converted from the image file
    """
    skimg = numpy.array(img) # Convert PIL image to skimage
    return skimage_to_digit_string(skimg, whitelistchars, removeboundingbox)

def skimage_to_digit_string(skimg, whitelistchars="0123456789", removeboundingbox=True, filename=None):
    """Converts an image that contains digits to a string.

    Args:
        skimg: RGB represented ndarray image for skimage library
        whitelistchars (Optional): String of letters to be recognized by the OCR
                                   By default, it is set to only recognize digits.
                                   Change this value if you want OCR to recognize different symbols/letters,
                                   but having too many characters here can drop the accuracy.
        removeboundingbox (Optional): If True, it will automatically detect and remove bounding boxes from the image.
                                      If accuracy is very low, try switching this to false.

    Returns:
        String of digits converted from the image.
    """

    #skimg = _filter_skimage(skimg, removeboundingbox) # Apply filters to the image
    skimg = image_filter(skimg, removeboundingbox) # Apply filters to the image

    """
    if DEBUG_OUTPUT_TMP_IMG_FLAG:
        temp_imagefile = "tmp.png"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore") # Suppress warning message
            skimage.io.imsave(temp_imagefile, skimg) # Save image to temp file
    """


    pil_img = PIL.Image.fromarray(skimg.astype('uint8'), 'L') # Convert skimage to PIL

    temp_imagefile = ".".join(filename.strip().split(".")[:-1]) + "_tmp.png"
    if DEBUG_OUTPUT_TMP_IMG_FLAG:
        temp_imagefile = "tmp.png"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Suppress warning message

        pil_img.save(temp_imagefile, dpi=(300, 300))

    result_file_path = ".".join(filename.strip().split(".")[:-1]) + "_result"
    cmd = "tesseract " + temp_imagefile + " " + result_file_path + " -c tessedit_char_whitelist=" + whitelistchars + " --psm 6 --oem 0"
    p = subprocess.Popen(cmd, shell=True)
    p.wait()

    readfile = open(result_file_path + ".txt", 'r')
    text = readfile.readline().strip().replace(" ", "").replace("\n", "") # Convert image to digit string
    readfile.close()
    answer = text

    # Post processing to handle suspicious recognitions
    answer = _post_process(skimg, answer, whitelistchars, temp_imagefile, result_file_path)


    return answer


def image_filter(img, removeboundingbox=True):
    """
    Applies several filters to the image for better OCR accuracy

    Args:
        img: RGB represented ndarray image for skimage library
        removeboundingbox (Optional): If True, it will automatically detect and remove bounding boxes from the image.
                                      If accuracy is very low, try switching this to false.

    Returns:
        filtered ndarray image
    """
    _save_temp_image(img, processname="original", resetcounter=True)

    COLOR_BLACK = 0
    COLOR_WHITE = 255

    # Convert to grayscale
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _save_temp_image(img, processname="grayscale")

    # Remove bounding box
    if removeboundingbox:
        img = _remove_bbox(img) # Remove bounding box
        _save_temp_image(img, processname="removeBorders")

    # Apply Otsu thresholding
    thresh = filters.threshold_otsu(img) # Find otsu threshold
    img_mask = (img > thresh) * 255 # Apply otsu thresholding
    img_mask = img_mask.astype('uint8')
    _save_temp_image(img_mask, processname="otsu_mask")

    # Crop the image so only digits are present in the image
    # Find the top left and bottom right corners of the digits, assuming letters are always black
    black_min_x = LARGE_NUMBER  # very large number
    black_min_y = LARGE_NUMBER
    black_max_x = SMALL_NUMBER
    black_max_y = SMALL_NUMBER
    black_count = 0

    white_min_x = LARGE_NUMBER  # very large number
    white_min_y = LARGE_NUMBER
    white_max_x = SMALL_NUMBER
    white_max_y = SMALL_NUMBER
    white_count = 0

    # enumerate over the pixels and get the region with ID
    # count the numbers of dark and light pixels to determine whether the background is dark or light
    for x in range(0, img_mask.shape[1]):
        for y in range(0, img_mask.shape[0]):
            if img_mask[y][x] == COLOR_BLACK:  # This pixel is black
                black_min_x = min(black_min_x, x)
                black_min_y = min(black_min_y, y)
                black_max_x = max(black_max_x, x)
                black_max_y = max(black_max_y, y)
                black_count += 1
            elif img_mask[y][x] == COLOR_WHITE:  # This pixel is white
                white_min_x = min(white_min_x, x)
                white_min_y = min(white_min_y, y)
                white_max_x = max(white_max_x, x)
                white_max_y = max(white_max_y, y)
                white_count += 1

    isWhiteBackground = True
    textStartLoc = (black_min_x, black_min_y)
    textEndLoc = (black_max_x + 1, black_max_y + 1)
    if black_count > white_count:  # If black is the background color
        textStartLoc = (white_min_x, white_min_y)
        textEndLoc = (white_max_x + 1, white_max_y + 1)
        isWhiteBackground = False

    # Choose how many pixels to expand from letters
    expandX = EXPAND_PIXEL_NUMBER
    expandY = EXPAND_PIXEL_NUMBER
    height, width = img.shape
    newImgStartLoc = (max(0, textStartLoc[0] - expandX), max(0, textStartLoc[1] - expandY))
    newImgEndLoc = (min(width, textEndLoc[0] + expandX), min(height, textEndLoc[1] + expandY))
    img = img[newImgStartLoc[1]:newImgEndLoc[1], newImgStartLoc[0]:newImgEndLoc[0]]
    _save_temp_image(img, processname="crop")

    # Scale the image. Make height to be 50 and resize width using the same scale ratio
    maxheight = FIXED_HEIGHT
    height, width = img.shape
    scaleratio = float(maxheight / height)
    newwidth = int(width * scaleratio)
    newheight = int(height * scaleratio)

    img = cv2.resize(img, (newwidth, newheight), interpolation=cv2.INTER_AREA)
    _save_temp_image(img, processname="resize")

    # If background color is black, flip the colors
    if not isWhiteBackground:
        img = 255 - img
    _save_temp_image(img, processname="color_flip")

    # Binarize the newly cropped and flip image
    thresh = filters.threshold_otsu(img)  # Find otsu threshold
    img_mask = (img > thresh) * 255  # Apply otsu thresholding
    img_mask = img_mask.astype('uint8')
    _save_temp_image(img, processname="otsu_mask2")

    # Remove leading colon
    backgroundcolor = _get_background_color(img)
    intervals = _get_interval(img_mask)  # get the column intervals between characters
    word_blocks = list(_get_complement(intervals, 0, width-1))  # the word blocks are the complement of the intervals
    height_list = []

    # For each word block, get the height of the character and put it into height_list
    for block in word_blocks:
        start_index = 0
        end_index = newheight-1
        for i in range(newheight):
            if img_mask[i, block[0]:block[1]].all() != (255*numpy.ones(block[1]-block[0])).all():
                start_index = i
                break
        for i in range(newheight-1, -1, -1):
            if img_mask[i, block[0]:block[1]].all() != (255*numpy.ones(block[1]-block[0])).all():
                end_index = i
                break
        height_list.append((end_index-start_index+1))

    # threshold is the median of the height_list
    threshold = numpy.percentile(numpy.array(height_list), 50)

    # if the leading character's height is smaller than the threshold*HEIGHT_RATIO
    # we can assume the leading character is colon
    # we can then remove it by coloring to the background color
    if height_list[0] < threshold * HEIGHT_RATIO:
        img[:, max(word_blocks[0][0]-1, 0):min(word_blocks[0][1]+2, width)] = backgroundcolor

    if height_list[-1] < threshold * HEIGHT_RATIO:
        img[:, max(word_blocks[-1][0] - 1, 0):min(word_blocks[-1][1] + 2, width)] = backgroundcolor
    _save_temp_image(img, processname="remove_colon")

    '''
    img = cv2.medianBlur(img, 3)
    backgroundcolor = _get_background_color(img)
    '''

    # Pad the image with several pixels
    pad_width = int(img.shape[1] * PAD_WIDTH_RATIO)
    pad_height = int(img.shape[0] * PAD_HEIGHT_RATIO)

    def pad_with(vector, pad_width, iaxis, kwargs):
        pad_value = backgroundcolor
        vector[:pad_width[0]] = pad_value
        vector[-pad_width[1]:] = pad_value
        return vector
    img = numpy.pad(img, ((pad_height, pad_height), (pad_width, pad_width)), pad_with, axis=0)
    _save_temp_image(img, "padding")

    return img


# -------------------------- INTERNAL FUNCTIONS ---------------------------------

def _get_interval(img):
    """(Internal function, Do not call from outside)
    Get intervals between characters
    :param img: binary image
    :return: a list of tuples represents a list of intervals
    """
    rotated = img.transpose(1, 0)
    height, width = rotated.shape
    bgRow = numpy.array([255]*width)
    flag = False
    start = -1
    lst = []
    for i in range(height):
        if (abs(bgRow-rotated[i])).sum() < 255:
            if not flag:
                flag = True
                start = i
                end = start
            else:
                end = max(start, i)
        else:
            flag = False
            if start >= 0:
                lst.append((start, end))
                start = -1

    if flag == True:
        lst.append((start, end))

    return lst

def _get_complement(intervals, mn, mx):
    """(Internal function, Do not call from outside)
    Get word blocks from intervals
    :param intervals: a list of tuple represents a a list of intervals,
                    each tuple is a pair (start, end), represents the span of the interval
    :param mn: span start
    :param mx: span end
    :return: word blocks(generator)
    """
    next_start = mn
    for x in intervals:
        if next_start < x[0]:
            yield next_start, x[0]-1
            next_start = x[1]+1
        elif next_start < x[1]:
            next_start = x[1]+1
    if next_start < mx:
        yield next_start, mx

def _post_process(skimg_preprocess, answer, whitelistchars, input_img_file_path, result_file_path):
    """(Internal function, Do not call from outside)
    After digit recognition, if there are some skeptical letters (such as 'Z' vs '2'), this function will handle those cases

    Args:
        skimg_preprocess: Sitk image after pre-processing
        answer: Answer string that tesseract returned
        whitelistchars: White list characters
        input_img_file_path: Path to the pre-processed image file
        result_file_path: Path to the output result file

    Returns:
        Corrected answer string
    """
    bbox_dict = None

    answer, bbox_dict = _post_process_2andZ(skimg_preprocess, answer, whitelistchars, bbox_dict, input_img_file_path, result_file_path)

    return answer


def _binarize_image(img):
    """(Internal function, Do not call from outside)
    Binarize a grayscale image and flip the color if the background is dark

    Args:
        img: ndarray image (Shape must be 2-D which represents a grayscale image)

    Returns:
        Binary image
    """
    ret, otsu = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    unique, counts = numpy.unique(otsu, return_counts=True)
    cnt = dict(zip(unique, counts))
    if 0 in cnt and 255 in cnt and cnt[0] > cnt[255]:
        otsu = 255-otsu

    return otsu

def _get_background_color(img):
    """(Internal function, Do not call from outside)
    Finds the most common color in a grayscale image

    Args:
        img: ndarray image (Shape must be 2-D which represents a grayscale image)

    Returns:
        Most frequent grayscale value between 0 - 255
    """
    (values, counts) = numpy.unique(img, return_counts=True)
    ind = numpy.argmax(counts)

    return values[ind]


def _get_index(img, bg_color, mode):
    """(Internal function, Do not call from outside)
    Finds the indices of rows(or columns) that contain border lines

    Args:
        img: 2-D ndarray image (grayscale or binary)
        bg_color: background color, an integer value between 0 and 255
        mode: specify finding rows or columns

    Returns:
        index: a list of indices that contains a line that has a different with background, length is longer than a ratio and the line touches the border of the image
        row: a list of lists, each element is a four elements list that represents a row(column) that contains a line longer than a ratio [index, start, end, color]
    """
    h, w = img.shape
    index = []
    row = []
    for i in range(h):
        bits = img[i]
        n = bits.shape[0]
        loc_run_start = numpy.empty(n, dtype=bool)
        loc_run_start[0] = True
        numpy.not_equal(bits[:-1], bits[1:], out=loc_run_start[1:])
        run_starts = numpy.nonzero(loc_run_start)[0]  # start of consecutive values
        run_values = bits[loc_run_start]  # consecutive value, which is the color of pixels
        run_lengths = numpy.diff(numpy.append(run_starts, n))  # length of consecutive value

        # remove dashed line borders
        for j in range(len(run_lengths) - 1):
            len_element = [run_lengths[j], run_lengths[j + 1]]  # repeating length pattern element
            val_element = [run_values[j], run_values[j + 1]]  # repeating pixel color pattern element
            total_length = numpy.sum(run_lengths)
            times = int(total_length * REMOVE_BORDER_LINE_RATIO) // (len_element[0] + len_element[1])  # repeating times threshold
            len_repeat = numpy.tile(len_element, times)
            val_repeat = numpy.tile(val_element, times)
            if times >= 3 and j + times * 2 <= len(run_lengths) and \
                    numpy.array_equal(len_repeat, run_lengths[j:j + times * 2]) and \
                    numpy.array_equal(val_repeat, run_values[j:j + times * 2]):
                index.append(i)
                break

        for j in range(len(run_starts)):
            if run_values[j] != bg_color and run_lengths[j] > int(w*REMOVE_BORDER_LINE_RATIO):
                if mode == "row":
                    row.append([i, run_starts[j], run_starts[j]+run_lengths[j], run_values[j]])
                elif mode == "col":
                    row.append([i, run_starts[j], run_starts[j]+run_lengths[j], run_values[j]])

            if run_values[j] != bg_color and run_lengths[j] > int(w*REMOVE_BORDER_LINE_RATIO) and \
                    (run_starts[j] == 0 or run_starts[j]+run_lengths[j]==w):
                index.append(i)

    return index, row


def _remove_bbox_part(maskImg, img):
    """
    Find borders in maskImg and set their color to background in img

    Args:
        maskImg: grayscale or binary image
        img: image

    Returns:
        img: which has borders removed
    """
    mask_bg_color = _get_background_color(maskImg)
    rowIndex, rows = _get_index(maskImg, mask_bg_color, "row")
    colIndex, cols = _get_index(maskImg.transpose(1,0), mask_bg_color, "col")
    for row in rows:
        for col in cols:
            if row[1] <= col[0] <= row[2] and abs(int(col[3])-int(row[3]))<3:
                # rowIndex.append(row[0])
                colIndex.append(col[0])
    colIndex = list(set(colIndex))
    # rowIndex = list(set(rowIndex))

    bg_color = _get_background_color(img)
    for i in colIndex:
        img[:,i] = bg_color
    #for i in rowIndex:
    #    img[i,:] = bg_color

    return img


def _remove_bbox(img):
    """(Internal function, Do not call from outside)
    Find borders in grayscale and binary versions of the image and remove them

    Args:
        img: 2-D grayscale ndarray image

    Returns:
        img: 2-D grayscale ndarray image with its borders removed
    """
    removed = _remove_bbox_part(img, img)
    (values,counts) = numpy.unique(removed, return_counts=True)
    if len(values) == 1:
        return removed
    binaryImg = _binarize_image(removed)
    removed = _remove_bbox_part(binaryImg, img)

    return removed



def _post_process_2andZ(skimg_preprocess, answer, whitelistchars, bbox_dict, input_img_file_path, result_file_path):
    """(Internal function, Do not call from outside)
    2 and Z are not distinguished correctly in tesseract, so we manually look into this case.

    Args:
        skimg_preprocess: Sitk image after pre-processing
        answer: Answer string that tesseract returned
        whitelistchars: White list characters
        bbox_dict: Bounding box dictionary for each letter if other post-processing function already generated this.
                   If not, specify None
        input_img_file_path: Path to the preprocessed image file
        result_file_path: Path to the output file

    Returns:
        Tuple of (corrected_answer, bbox_dict)
            corrected_answer: Corrected answer string
            bbox_dict: Bounding box dictionary for each letter
    """
    if len(answer) == 0:
        return answer, bbox_dict

    if '2' not in whitelistchars or 'Z' not in whitelistchars or (answer[0] != "Z" and answer[0] != "2"):
        return answer, bbox_dict

    if bbox_dict is None:
        pass
        pytesseract_config = "-c tessedit_char_whitelist=" + whitelistchars + " --psm 6 --oem 0"
        bbox_dict = pytesseract.image_to_boxes(skimg_preprocess, config=pytesseract_config, output_type=pytesseract.Output.DICT)
        #corrected_answer = pytesseract.image_to_string(skimg_preprocess, config=pytesseract_config)

    char_list = bbox_dict["char"]
    if len(char_list) == 0:
        return answer, bbox_dict

    corrected_answer = list(answer)

    # TODO: For now, we only care about the first character
    # If in the future, if we need to detect Z in the middle, consider looping through all letters
    #for i in range(0, len(char_list)):
    for i in range(0, 1):
        if not answer[i] == "Z" and not answer[i] == "2":
            continue

        print("Found letter that is either 2 or Z")
        x1 = bbox_dict["left"][i]
        x2 = bbox_dict["right"][i]
        y1 = bbox_dict["bottom"][i]
        y2 = bbox_dict["top"][i]

        if x2 - x1 >= y2 - y1:
            # width should be no larger than height
            x2 = x1 + (y2 - y1)

        letter_img = skimg_preprocess[y1:y2, x1:x2]
        _save_temp_image(letter_img, "crop_letter")

        letter_top_pixel_list = []
        top_total = 0
        for x in range(0, letter_img.shape[1]):
            top_pixel = -1
            for y in range(0, 10): # Search for top 10 pixels
                if letter_img[y][x] == 0:
                    top_pixel = y
                    break
            if top_pixel != -1:
                letter_top_pixel_list.append(top_pixel)
                top_total += top_pixel

        average_top = top_total / len(letter_top_pixel_list)
        top_variance = 0
        for top_pixel in letter_top_pixel_list:
            top_variance += (top_pixel - average_top) ** 2
        top_variance = top_variance / len(letter_top_pixel_list)

        z_variance_threhsold = 0.7

        correct_letter = ""
        if top_variance <= z_variance_threhsold:
            # This letter is Z
            correct_letter = 'Z'
        else:
            # This letter is 2
            correct_letter = '2'

        corrected_answer[i] = correct_letter

        print(str(i) + ": top_variance = " + str(top_variance) + ", prediction = " + correct_letter)
        """
        for y in range(0, letter_img.shape[0]):
            black_pixel_num = letter_img.shape[1] - int(numpy.sum(letter_img[y] / 255))
            print("black_pixel_num = " + str(black_pixel_num))
        """


    return "".join(corrected_answer), bbox_dict
    """
    cmd = "tesseract.exe " + input_img_file_path + " " + result_file_path + " -c tessedit_char_whitelist=" + whitelistchars + " --psm 6 --oem 1"
    p = subprocess.Popen(cmd, shell=True)
    p.wait()

    readfile = open(result_file_path + ".txt", 'r')
    text = readfile.readline().strip().replace(" ", "").replace("\n", "") # Convert image to digit string
    readfile.close()
    z_answer = text

    two_z_order = ""
    for letter in z_answer:
        if letter == 'Z' or letter == '2':
            two_z_order += letter

    two_z_order_counter = 0
    corrected_answer = list(answer)
    for i in range(0, len(answer)):
        if answer[i] == 'Z' or answer[i] == '2':
            if two_z_order_counter < len(two_z_order):
                corrected_answer[i] = two_z_order[two_z_order_counter]
                two_z_order_counter += 1


    #corrected_answer = "".join(bbox_dict["char"])
    return "".join(corrected_answer), bbox_dict
    """

def _save_temp_image(skimg, processname, resetcounter=False):
    """(Internal function, Do not call from outside)
    Saves a temporary image to file. Debug purpose only

    Args:
        skimg: ndarray image for skimage library
        processname: String that represents the filter process name
        resetCounter (Optional): Set this to true if you want to reset the filename counter
    """
    if DEBUG_OUTPUT_TMP_STEP_IMAGES_FLAG == False:
        return

    if resetcounter == True:
        _save_temp_image.filecounter = 0

    counter_str = "%02d" % _save_temp_image.filecounter
    filename = "tmp_" + counter_str + "_" + processname + ".png"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # Suppress warning message
        skimage.io.imsave(filename, skimg) # Save image to temp file

    _save_temp_image.filecounter += 1

#def _draw_histogram(skimg_grayscale, processname):
#    """(Internal function, Do not call from outside)
#    Draws histogram of a grayscale image
#
#    Args:
#        skimg_grayscale: 2-D grayscale ndarray image
#        processname: String that represents the filter process name
##    """
#   if DEBUG_OUTPUT_TMP_STEP_IMAGES_FLAG == False:
#        return
#
#    skimg_int = (skimg_grayscale * 255).astype(int)
#
#    print("Histogram after " + processname + ":")
#    print(skimage.exposure.histogram(skimg_int))
#
#    hist = skimage.exposure.histogram(skimg_int)
#    (listy, listx) = hist
#    #plt.plot(listx, listy, 'r--', linewidth=1)
#    plt.plot(listx, listy, '.', linewidth=1)
#    plt.xlabel("Grayscale color")
#    plt.ylabel("Frequency")
#    plt.title("Histogram after " + processname)
#    plt.grid(True)
#    plt.show()
