import json
import os
import pickle
import logging
import subprocess
from collections import Counter
from os import listdir
from os.path import isfile, join

import cv2
import numpy as np
import PIL
from sklearn.svm import SVC

from ocr.engine import __version__
from ocr.engine.image2string import image_filter, imagefile_to_digit_string, _get_index
from ocr.engine.pattern import ConvertStrToPatternList, PatternMatching

_logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), 'svm.sav'), 'rb') as f:
    CLF = pickle.load(f)


class SetupNotJustOneFileError(Exception):
    pass


class SetupOnlyOneColorError(Exception):
    pass


class EmptyImageError(Exception):
    pass


# Analyse image color
class ColorAnalyser:
    def __init__(self, img):
        self.src = img
        self.colors_count = {}

    def count_colors(self):
        (channel_b, channel_g, channel_r) = cv2.split(self.src)

        channel_b = channel_b.flatten()
        channel_g = channel_g.flatten()
        channel_r = channel_r.flatten()

        for i in range(len(channel_b)):
            BGR = (channel_b[i], channel_g[i], channel_r[i])
            if BGR in self.colors_count:
                self.colors_count[BGR] += 1
            else:
                self.colors_count[BGR] = 1

    def show_colors(self):
        for keys in sorted(self.colors_count, key=self.colors_count.__getitem__, reverse=True):
            print(keys, ": ", self.colors_count[keys])

    def get_background_color(self):
        self.count_colors()
        return max(self.colors_count, key=lambda key: self.colors_count[key])


class SigmaOCR:
    def __init__(self, pattern_str=''):
        self.whitelist_char = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        self.len = -1
        self.bgColorSet = set([])
        self.offset = 10
        if pattern_str:
            converter = ConvertStrToPatternList(pattern_str)
            converter.process()
            self.pattern = converter.get_pattern_list()
        else:
            self.pattern = []
        _logger.info("------You are running SigmaOCR Version %s ------" % __version__)

    def reset(self, jsonfile):
        try:
            os.remove(jsonfile)
        except OSError:
            pass

    @staticmethod
    def tesseract(image_file, result_file, whitelist):
        # call tesseract for OCR
        cmd = [
            'tesseract', image_file, result_file,
            '-c', 'tessedit_char_whitelist={}'.format(whitelist),
            '--psm', '6', '--oem', '0', '-l', 'combine'
        ]
        subprocess.call(cmd, shell=False)
        # read result file and return the result
        with open(result_file + '.txt') as f:
            text = f.readline().strip().replace(" ", "").replace("\n", "")
            return text

    def ocr_process(self, json_file, image_dir, threshold, patient_id=''):
        if patient_id:
            return self.ocr_setup(json_file, image_dir, patient_id)
        else:
            return self.ocr_apply(json_file, image_dir, threshold)

    def ocr_legacy(self, image_file):
        return imagefile_to_digit_string(image_file, self.whitelist_char, removeboundingbox=False)

    def ocr_setup(self, json_file, image_dir, patient_id):
        assert patient_id
        _logger.info('ocr setup: {}'.format(image_dir))
        # add background color of the image to the bgColorSet
        try:
            img_list = [join(image_dir, f) for f in listdir(image_dir) if isfile(join(image_dir, f))]
            if len(img_list) != 1:
                raise SetupNotJustOneFileError
            else:
                img = cv2.imread(img_list[0])
                if img.size:
                    color_count, bg_color = self._get_colors(img)
                else:
                    raise EmptyImageError
                if len(color_count) == 1:
                    raise SetupOnlyOneColorError
        except SetupNotJustOneFileError:
            _logger.warning("There should be exactly one file in the folder")
            return ""
        except SetupOnlyOneColorError:
            _logger.warning("There is only one color in the image")
            return ""
        except EmptyImageError:
            _logger.warning("The image is empty")
            return ""

        # row cropping
        binary_img = self._image_binarize(img)
        lower, upper = self._row_cropping(binary_img, pos=True)
        img = img[lower:upper]

        # calculate threshold for column cropping
        intervals = self._get_interval(binary_img[lower:upper])
        thres = -1
        for itv in intervals:
            if itv[0] <= self.offset <= itv[1]:
                thres = itv[1] - itv[0] + 1
                break

        if thres < 0:
            _logger.warning("BBox shouldn't be on the ID")
            return "BBox shouldn't be on the ID", thres
        _logger.info("thres: {}".format(thres))

        if self.offset > 0:
            img = img[:, self.offset:-self.offset, :]
            img = cv2.resize(img, (300, 64), interpolation=cv2.INTER_LINEAR)

        # image preprocessing
        img = image_filter(img)

        pil_img = PIL.Image.fromarray(img.astype('uint8'), 'L')
        prefix_name = join(image_dir, os.path.splitext(os.path.basename(img_list[0]))[0])
        temp_image_file = "{}_tmp.png".format(prefix_name)
        result_file_path = "{}_tmp".format(prefix_name)
        pil_img.save(temp_image_file, dpi=(300, 300))

        # call tesseract for OCR
        text = self.tesseract(temp_image_file, result_file_path, self.whitelist_char)

        if self.pattern:
            match = PatternMatching(text, self.pattern)
            match.process()
            converted_text = match.get_potential_result()
            if converted_text:
                text = converted_text[0]['converted_pid']

        # save the json file only if the recognition is correct
        # if text == patient_id:
        if thres >= 0:
            params = {'bgColor': [list(map(int, bg_color))]}
            self._json_dump(params, json_file)
        return text, thres

    def ocr_apply(self, json_file, image_dir, threshold):
        # get all file names in the folder
        img_name_list = [join(image_dir, f) for f in listdir(image_dir) if isfile(join(image_dir, f))]

        with open(json_file, 'r') as f:
            params = json.load(f)

        # some initial filtering of the images
        img_list = []
        name_list = []
        for imgName in img_name_list:
            _logger.info('ocr apply: {}'.format(imgName))
            img = cv2.imread(imgName)
            if img.size:
                color_count, bg_color = self._get_colors(img)
            else:
                _logger.warning("Empty image: {}".format(imgName))
                continue

            if len(color_count) == 1:
                _logger.warning("Only one color in this image: {}".format(imgName))
                continue
            bg_color = list(map(int, bg_color))

            if not self._bg_color_has_appeared(bg_color, params['bgColor']):
                # if the background color of the image is not among the background colors at setup up,
                # filter out the image
                _logger.warning("Background color filterled: {}".format(imgName))
                continue
            else:
                binary_img = self._image_binarize(img)
                if not self._has_foreground(binary_img):
                    # if the center row of the image has no foreground, filter out the image
                    _logger.warning("Centerline no foreground: {}".format(imgName))
                    continue
                else:
                    basename = os.path.basename(imgName)
                    thres = threshold.get(basename, 1)
                    print('thres: ', thres)
                    prefix_name = join(image_dir, os.path.splitext(basename)[0])

                    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    img = self._remove_bbox_part(img_gray, img, bg_color)
                    img = self._remove_bbox_part(binary_img, img, bg_color)
                    binary_img = self._image_binarize(img)

                    upper, lower = self._row_cropping(binary_img, True)
                    img = img[upper:lower]

                    cv2.imwrite("{}_cropped.png".format(prefix_name), img)
                    intervals = self._get_interval(binary_img[upper:lower])
                    left = -1
                    margin = 0
                    for pos, itv in enumerate(intervals):
                        if itv[1]-itv[0]+1 >= thres-1 and pos < len(intervals)/2:
                            left = itv[1]+1-(itv[1]-itv[0])//2
                            margin = (itv[1]-itv[0])//2
                            break

                    img_transpose = img.transpose(1, 0, 2)
                    width = img_transpose.shape[0]
                    right_bound = min(left+width-2*self.offset+margin, width-1)
                    if left >= 0:
                        img_transpose_cropped = img_transpose[left:right_bound]
                    else:
                        img_transpose_cropped = img_transpose[:-self.offset]

                    img = cv2.resize(img_transpose_cropped,(64, 300), interpolation=cv2.INTER_LINEAR)
                    img_list.append(img)
                    name_list.append(imgName)

        if not img_list:
            _logger.warning('Valid image not found in {}'.format(image_dir))
            return ''

        # extract the HOG features from all the images
        gradient_list = []
        self._compute_HOGs(img_list, gradient_list)

        # classifiy the image on their HOG features
        class_prediction = CLF.predict(np.array(gradient_list))
        # print(class_prediction)
        results = []
        for i, v in enumerate(class_prediction):
            # if is classified valid, processed the image and put into OCR engine
            if v == 1:
                prefix_name = join(image_dir, os.path.splitext(os.path.basename(name_list[i]))[0])
                img = img_list[i].transpose(1,0,2)
                cv2.imwrite("{}_abc.png".format(prefix_name), img)
                img = image_filter(img)
                pil_img = PIL.Image.fromarray(img.astype('uint8'), 'L')
                temp_image_file = "{}_tmp.png".format(prefix_name)
                result_file_path = "{}_tmp".format(prefix_name)
                pil_img.save(temp_image_file, dpi=(300, 300))
                text = self.tesseract(temp_image_file, result_file_path, self.whitelist_char)
                if self.pattern:
                    match = PatternMatching(text, self.pattern)
                    match.process()
                    converted_text = match.get_potential_result()
                    if converted_text:
                        text = converted_text[0]['converted_pid']

                if self.len <= 0 or len(text) == self.len:
                    results.append(text)

        counter = Counter(results)
        most = counter.most_common(1)
        return most and most[0][0] or ''

    @staticmethod
    def _json_dump(para, jsonfile):
        if not os.path.isfile(jsonfile) or os.stat(jsonfile).st_size == 0:
            f = open(jsonfile, 'w')
            json.dump(para, f)
            f.close()
        else:
            f = open(jsonfile, 'r+')
            prv = json.load(f)
            bg_color = prv['bgColor'] + para['bgColor']
            para = {'bgColor': bg_color}
            f.seek(0)
            json.dump(para, f)
            f.truncate()
            f.close()

    @staticmethod
    def _has_foreground(img):
        height, width = img.shape[:2]
        bg_row = np.array([255]*width)
        if (abs(bg_row-img[height//2])).sum() < width/20*255:
            return False
        else:
            return True

    @staticmethod
    def _image_binarize(img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, otsu = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        unique, counts = np.unique(otsu, return_counts=True)
        cnt = dict(zip(unique, counts))
        if 0 in cnt and 255 in cnt and cnt[0] > cnt[255]:
            otsu = 255-otsu
        return otsu

    def set_whitelist_char(self, whitelist):
        self.whitelist_char = whitelist

    def set_length(self, length):
        self.len = length

    def set_offset(self, offset):
        self.offset = offset

    @staticmethod
    def _compute_HOGs(img_lst, gradient_lst):
        hog = cv2.HOGDescriptor()
        for i in range(len(img_lst)):
            roi = img_lst[i]
            features = hog.compute(roi)
            gradient_lst.append(features.flatten())

    def _set_bg_color(self, img_name):
        analyser = ColorAnalyser(img_name)
        bg_color = analyser.get_background_color()
        self.bgColorSet.add(bg_color)

    @staticmethod
    def _get_colors(img):
        analyser = ColorAnalyser(img)
        analyser.count_colors()
        color_count = analyser.colors_count
        bg_color = analyser.get_background_color()
        return color_count, bg_color

    def _row_cropping(self, img, pos=False):
        if self.offset > 0:
            img = img[:, self.offset:-self.offset]

        height, width = img.shape[:2]
        margin = int(height*0.1)
        center_y = int(height/2)
        min_row = center_y
        flag = False
        bg_row = np.array([255]*width)
        upper = 0
        for i in range(center_y, 0, -1):
            if len(np.extract(bg_row-img[i] > 3, bg_row-img[i])) > len(bg_row)//15:
                flag = True
                min_row = min(min_row, i)
            elif flag:
                upper = min_row
                break
            else:
                upper = 0

        upper = max(0, upper-margin)

        flag = False
        max_row = 0
        lower = height - 1
        for i in range(center_y, height):
            if len(np.extract(bg_row-img[i] > 3, bg_row-img[i])) > len(bg_row)//15:
                flag = True
                max_row = max(max_row, i)
            elif flag:
                lower = max_row
                break
            else:
                lower = height-1

        lower = min(lower+margin, height-1)
        if not pos:
            img = img[upper:lower+1]
            return img
        else:
            return upper, lower+1

    @staticmethod
    def _bg_color_has_appeared(bg_color, bg_color_set):
        bg_color = np.array(bg_color)
        bg_color_set = np.array(bg_color_set)
        diff_array = abs(bg_color - bg_color_set)
        flag_list = []
        for diff in diff_array:
            f = np.all(diff < 5)
            flag_list.append(f)
        return np.array(flag_list).any()

    @staticmethod
    def _get_interval(img):
        rotated = img.transpose(1, 0)
        height, width = rotated.shape[:2]
        bg_row = np.array([255]*width)
        flag = False
        start = -1
        end = -1
        lst = []
        for i in range(height):
            if (abs(bg_row-rotated[i])).sum() < 255:
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

        if flag:
            lst.append((start, end))

        return lst

    @staticmethod
    def _get_background_color(img):
        """(Internal function, Do not call from outside)
        Finds the most common color in a grayscale image

        Args:
            img: ndarray image (Shape must be 2-D which represents a grayscale image)

        Returns:
            Most frequent grayscale value between 0 - 255
        """
        (values, counts) = np.unique(img, return_counts=True)
        ind = np.argmax(counts)

        return values[ind]

    def _remove_bbox_part(self, mask_img, img, bg_color):
        mask_bg_color = self._get_background_color(mask_img)
        row_index, rows = _get_index(mask_img, mask_bg_color, "row")
        col_index, cols = _get_index(mask_img.transpose(1, 0), mask_bg_color, "col")
        for row in rows:
            for col in cols:
                if row[1] <= col[0] <= row[2] and abs(int(col[3])-int(row[3])) < 3:
                    # row_index.append(row[0])
                    col_index.append(col[0])
        col_index = list(set(col_index))
        # row_index = list(set(row_index))
        for i in col_index:
            img[:, i] = bg_color
        #for i in row_index:
        #    img[i, :] = bg_color

        return img
