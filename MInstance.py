"""
MInstance class
Independent instance of a minesweeper game
contains information about a single game of minesweeper on the screen

"""
import cv2
import numpy as np
import MLogicPlugin
import math
import time
import pyautogui
from MCoordinate import MCoordinate
from MLogicPlugin import MLogicPlugin
import time
import win32api
import win32con


class MInstance:
    # flag must be last or 1 will (sometimes) overwrite it, this is a hacky solution but it should work fine
    # feature definiton value is tuple of (lower-hsv, upper-hsv, symmetry[TB,LR] )

    feature_definitions = {'1': ([85, 66, 130], [117, 255, 255], [0, 0]),
                           '2': ([44, 162, 87], [66, 255, 158], [0, 0]),
                           '3': ([0, 101, 144], [37, 255, 202], [1, 0]),
                           '4': ([97, 232, 64], [161, 255, 217], [0, 0]),
                           '5': ([0, 62, 107], [37, 255, 144], [0, 0]),
                           '6': ([63, 175, 96], [101, 255, 188], [0, 0]),
                           '8': ([0, 101, 144], [37, 255, 202], [1, 1]),
                           '7': ([0, 101, 144], [37, 255, 202], [0, 0]),
                           '99': ([0, 77, 188], [59, 255, 255], [0, 0])
                           }
    # feature_definitions = {'1':  ([85, 66, 130], [117, 255, 255], [0, 0])}
    id = 0

    def __init__(self, location_tuple):
        # locations (low,high)
        self.my_window_location, self.my_grid_location, self.tile_length = location_tuple
        self.grid_array = np.empty([30, 16])
        self.grid_array[:] = np.NaN
        self.flags = 0
        self.is_complete = False

        self.id = MInstance.id
        MInstance.id += 1

    def get_id(self):
        print(self.id)

    def update(self, screen_snapshot):
        start = cv2.getTickCount()
        # DEBUG: RUN TIME ~.609


        if self._detect_window_popup(screen_snapshot):
            # if this hits true trigger reset sequence.
            print("Window Detected")
            pass
        # start2= cv2.getTickCount()
        self.update_array(screen_snapshot)  # DEBUG: OLD METHOD ~.32 SEC
        # end2 = cv2.getTickCount()
        # total = (end2 - start2) / cv2.getTickFrequency()
        # total
        self.debugarray = self.grid_array.transpose()
        # 1) Receives screen snapshot
        # 2) Updates own array
        # 3) Uses logic plugin
        # 4) Cursor action

        k = MLogicPlugin(1, 1)

        self.cursor_control(k[0], k[1])
        end = cv2.getTickCount()
        total = (end - start)/ cv2.getTickFrequency()
        total

        # self.cursor_control((5, 5), 'left')

    def reset(self):
        # print(self.grid_array)
        # self.grid_array = np.empty([30, 16])
        # self.grid_array[:] = np.NaN
        self.flags = 0
        self.is_complete = False
        self.cursor_control([0, 0], 'left')  # ensures the correct window is selected
        pyautogui.press('escape')  # pressing escape while a window popup is active will start a new game.
        # pyautogui.press('n')

    def cursor_control(self, location, action):  # tells cursor to perform action at specific array[x,y] location.

        cursor_offset_correction = MCoordinate(self.tile_length / 2, self.tile_length / 2)
        lower_window_real_location = self.my_window_location[0]
        lower_grid_real_location = lower_window_real_location + self.my_grid_location[0]
        x_target = lower_grid_real_location.x + cursor_offset_correction.x + self.tile_length * location[0]
        y_target = lower_grid_real_location.y + cursor_offset_correction.y + self.tile_length * location[1]

        # print("--------------------")
        # print(x_target)
        # print(y_target)
        # print("--------------------")





        # pyautogui.moveTo(x_target, y_target, duration=0)
        win32api.SetCursorPos((x_target, y_target))
        time.sleep(.01)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x_target, y_target, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x_target, y_target, 0, 0)
        # pyautogui.click(button=action)

    def update_array(self, screen_snapshot):

        #  process new screenshot into usable form
        lower_window_coords, upper_window_coords = self.my_window_location
        lower_grid_coords, upper_grid_coords = self.my_grid_location
        window = screen_snapshot[lower_window_coords.y:upper_window_coords.y,
                 lower_window_coords.x:upper_window_coords.x]
        grid_crop = window[lower_grid_coords.y:upper_grid_coords.y,
                    lower_grid_coords.x:upper_grid_coords.x]

        x = grid_crop.shape
        new_height = (x[0] + 16) - (x[0] % 16)
        new_width = (x[1] + 30) - (x[1] % 30)

        resized = cv2.resize(grid_crop, (new_width, new_height), interpolation=cv2.INTER_AREA)
        resized_hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        tt = resized.shape

        tile_height = round(new_height/16)
        tile_width = round(new_width/30)
        # tile_width = round(grid_width / 30)
        # tile_height = round(grid_height / 16)
        # tile_length = max(tile_height, tile_width)  # ensuring h and w are equal prevents drift from occuring

        cv2.imshow("resizaed", resized)
        cv2.imshow("gridcop", grid_crop)
        # cv2.waitKey(0)

        # create feature masks for whole grid that can be sliced to the individual tiles
        feature_masks = {}
        for feature, values in MInstance.feature_definitions.items():
            lower = np.array(values[0])
            upper = np.array(values[1])
            grid_mask = cv2.inRange(resized_hsv, lower, upper)
            # snapshot_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)  # set to grayscale
            grid_blur = cv2.GaussianBlur(grid_mask, (13, 13), 0)  # blur
            grid_bw = cv2.threshold(grid_blur, 50, 255, cv2.THRESH_BINARY)[1]
            feature_masks[feature] = grid_bw


        # create mask for empty tile, as its a special case it is separate

        lower = np.array([58, 0, 0])
        upper = np.array([177, 62, 255])
        grid_mask = cv2.inRange(resized_hsv, lower, upper)
        grid_blur = cv2.GaussianBlur(grid_mask, (13, 13), 0)  # blur
        grid_bw_empty_tile = cv2.threshold(grid_blur, 50, 255, cv2.THRESH_BINARY)[1]

        # DEBUG: ABOVE HERE TAKES APPROX .0737
        # DEBUG: TOTAL TIME FOR BELOW SECTION IS .35
        # DEBUG: APPROX TIME FOR 1 TILE OF BELOW CODE IS : .000978
        #OPTIMIZATION IDEA: move masking outside of loop and simply slice from it.
        for row in range(0, 16):
            tile_list = []
            for column in range(0, 30):
                x_target = tile_width * (row+1)
                y_target = tile_height * (column+1)
                # cv2.imshow("tile", tile_crop)
                # cv2.waitKey(0)
                match = False
                for feature, values in MInstance.feature_definitions.items():
                    tile_crop = feature_masks[feature][row * tile_width:x_target, column * tile_height:y_target]
                    match = self._detect_feature(values, tile_crop)
                    if match:
                        self.grid_array[column, row] = int(feature)
                        end = time.time()
                        break

                if not match:
                    # detecting 0 tiles requires an alternative method since contour detection fucks shit up fam.
                    tile_bw = grid_bw_empty_tile[row * tile_width:x_target, column * tile_height:y_target]
                    # tile_hsv = cv2.cvtColor(tile_crop, cv2.COLOR_BGR2HSV)
                    # lower = np.array([58, 0, 0])
                    # upper = np.array([177, 62, 255])
                    # mask = cv2.inRange(tile_hsv, lower, upper)
                    # tile_blur = cv2.GaussianBlur(mask, (13, 13), 0)  # blur
                    # tile_bw = cv2.threshold(tile_blur, 50, 255, cv2.THRESH_BINARY)[1]
                    tile_mean = tile_bw.mean()
                    if tile_mean/255 > .95:
                        self.grid_array[column, row] = int(0)
                    else:
                        self.grid_array[column, row] = np.NaN

    def _detect_window_popup(self,
                             screen_snapshot):  # this would occur on a won or lost game. Must differentiate between win / lose
        # print(screen_snapshot)
        return False

    def _detect_feature(self, values, tile_bw):

        # lower = np.array(values[0])
        # upper = np.array(values[1])
        symmetry = np.array(values[2])
        # mask = cv2.inRange(tile_hsv, lower, upper)
        #
        # # snapshot_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)  # set to grayscale
        # tile_blur = cv2.GaussianBlur(mask, (13, 13), 0)  # blur
        # tile_bw = cv2.threshold(tile_blur, 50, 255, cv2.THRESH_BINARY)[1]
        #
        # # cv2.imshow("mask", mask)
        # # cv2.imshow("BW", tile_bw)
        # # cv2.imshow("blurr", tile_blur)
        # # cv2.imshow("tile", tile)
        # # cv2.waitKey(0)

        contours, hierarchy = cv2.findContours(tile_bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for cont in contours:
            area = cv2.contourArea(cont)
            peri = cv2.arcLength(cont, True)
            approx = cv2.approxPolyDP(cont, .05 * peri, True)
            # cv2.drawContours(tile_hsv, [approx], -1, (0, 255, 0), 3)
            if 10 < area < (self.tile_length ** 2)/2:

            # if 10 < area:  # TEMPORARY DEBUG SWITCH BACK TO ORIGINAL
                moment = cv2.moments(cont)
                avg_x = int(moment["m10"] / moment["m00"])
                avg_y = int(moment["m01"] / moment["m00"])

                if symmetry[0] or symmetry[1]:

                    x, y, w, h = cv2.boundingRect(cont)
                    tile_feature_crop = tile_bw[y:y + h, x:x + w]
                    # cv2.drawContours(tile_hsv, [approx], -1, (0, 255, 0), 3)

                    top_bottom_symmetry = self._detect_symmetry(tile_feature_crop, 1)
                    left_right_symmetry = self._detect_symmetry(tile_feature_crop, 0)

                    # if only top-bottom symmetry required
                    if symmetry[0] and not symmetry[1]:
                        if top_bottom_symmetry > .75 and left_right_symmetry < .75:
                            # detected_coordinates.append(MCoordinate(avg_x, avg_y))
                            return True
                        else:
                            return False

                    # if only left-right symmetry required
                    if symmetry[1] and not symmetry[0]:
                        if left_right_symmetry > .75 and top_bottom_symmetry < .75:
                            # detected_coordinates.append(MCoordinate(avg_x, avg_y))
                            return True
                        else:
                            return False

                    # if both symmetry required
                    if symmetry[0] and symmetry[1]:
                        if left_right_symmetry > .75 and top_bottom_symmetry > .75:
                            # detected_coordinates.append(MCoordinate(avg_x, avg_y))
                            return True
                        else:
                            return False
                # cv2.circle(snapshot_hsv, (avg_x, avg_y), radius=8, color=(255, 255, 0), thickness = -1)
                return True
                # detected_coordinates.append(MCoordinate(avg_x, avg_y))

        return False

    @staticmethod
    def _detect_symmetry(tile_of_interest, is_vertical):

        # cv2.imshow("tileofinterest", tile_of_interest)
        # cv2.waitKey(0)

        nrow, ncol = tile_of_interest.shape
        # removes a row or col if total is odd, otherwise it will break
        if nrow % 2 != 0:
            tile_of_interest = tile_of_interest[:-1, :]
        if ncol % 2 != 0:
            tile_of_interest = tile_of_interest[:, :-1]
        nrow, ncol = tile_of_interest.shape

        rsplit, csplit = nrow // 2, ncol // 2

        top_bottom_symmetry = 0
        left_right_symmetry = 0

        if is_vertical:
            tile_upperhalf = tile_of_interest[:rsplit, :]
            tile_lowerhalf = tile_of_interest[rsplit:, :]
            tile_upperhalf_flipped = np.flip(tile_upperhalf, 0)
            top_bottom_intersection = cv2.bitwise_and(tile_lowerhalf, tile_upperhalf_flipped)
            top_bottom_union = cv2.bitwise_or(tile_lowerhalf, tile_upperhalf_flipped)
            top_bottom_symmetry = cv2.countNonZero(top_bottom_intersection) / \
                                  cv2.countNonZero(top_bottom_union)


            # cv2.imshow("tile_upperhalf_flipped", tile_upperhalf_flipped)
            # cv2.imshow("tile_lowerhalf", tile_lowerhalf)
            # cv2.waitKey(0)
            return top_bottom_symmetry

        if not is_vertical:
            tile_lefthalf = tile_of_interest[:, :csplit]
            tile_righthalf = tile_of_interest[:, csplit:]
            tile_lefthalf_flipped = np.flip(tile_lefthalf, 1)
            left_right_intersection = cv2.bitwise_and(tile_righthalf, tile_lefthalf_flipped)
            left_right_union = cv2.bitwise_or(tile_righthalf, tile_lefthalf_flipped)
            left_right_symmetry = cv2.countNonZero(left_right_intersection) / \
                                  cv2.countNonZero(left_right_union)

            # cv2.imshow("tile_lefthalg_flipped", tile_lefthalf_flipped)
            # cv2.imshow("tile_righthalf", tile_righthalf)
            # cv2.waitKey(0)
            return left_right_symmetry
