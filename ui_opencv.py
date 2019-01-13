import os
import sys
import cv2
import math
import shutil
import numpy as np


image_path = sys.argv[1] if len(sys.argv) > 1 else 'test.jpg'
MAX_WIDTH = 1600
MAX_HEIGHT = 900
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
PATH_INPUT = './decensor_input'
PATH_INPUT_ORIGINAL = './decensor_input_original'
PATH_OUTPUT = './decensor_output'

TIP = '''
r=開啟檔案
esc=退出
1=多邊形筆刷 2=矩形筆刷 3=圓形筆刷
ctrl+z=回上一步
b=輸出 (海苔條)
m=輸出 (馬賽克)
'''.strip('\n')

TIP2 = '''
===== 成功 =====
r=開啟檔案
esc=退出
e=返回編輯
s=原路徑儲存 (後輟_uncensored)
ctrl+s=另存新檔
'''.strip('\n')


workdir = os.path.dirname(sys.argv[0])
shape = 'polygon' # 1=polygon=多邊形 2=rectangle=矩形 3=circle=圓形
mouse_enabled = True
global image, tmp_image, tmp_point, tmp_points


class Point:
    RAD2DEG = 180 / math.pi
    DEG2RAD = math.pi / 180

    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def getDistance(self, point2):
        dx = point2.x - self.x
        dy = point2.y - self.y
        return math.sqrt(dx**2 + dy**2)

    def getAngle(self, point2):
        return self.RAD2DEG * math.atan2(point2.y - self.y, point2.x - self.x)

    def polarProjection(self, distance, angle):
        angle *= self.DEG2RAD
        return (
            int(self.x + distance * math.cos(angle)),
            int(self.y + distance * math.sin(angle)),
        )
    
    def __getitem__(self, key):
        return self.x if key == 0 else self.y if key == 1 else Exception('unknown key')


class Image:
    version = -1
    data = {}

    def __init__(self, path):
        self.path = path
        tmp_path = os.path.join(workdir, 'tmp%s' % os.path.splitext(path)[-1]) # copy到本地目錄 防止奇怪的名稱不能讀取的問題
        shutil.copyfile(path, tmp_path)
        image_cv_data = cv2.imread(tmp_path)
        if image_cv_data is None:
            raise Exception('ERROR: can not read %s' % path)
        self.update(image_cv_data)
        self.first = self.data[0]
        #如果視窗過大 進行縮放
        height, width, channels = self.last.shape
        self.scaling_ratio = min(1, MAX_WIDTH / width, MAX_HEIGHT / height)

    def update(self, image_cv_data):
        self.version += 1
        self.data[self.version] = image_cv_data
        self.last = image_cv_data

    def rollback(self):
        if self.version > 0:
            del self.data[self.version]
            self.version -= 1
            self.last = self.data[self.version]
            self.show()

    def __call__(self):
        return cv2.resize(self.last.copy(), (0, 0), fx=self.scaling_ratio, fy=self.scaling_ratio)

    def originalPoint(self, point):
        x = int(point[0] / self.scaling_ratio)
        y = int(point[1] / self.scaling_ratio)
        return Point(x, y) if type(point) == Point else (x, y)

    def show(self):
        cv2.imshow('image', self.__call__())


def onMouse(event, x, y, flags, param):
    global image, mouse_enabled, tmp_image, tmp_point, tmp_points
    if not image or not mouse_enabled:
        return

    if event == cv2.EVENT_LBUTTONDOWN: #左鍵點擊
        tmp_image = image()
        if shape == 'polygon':
            tmp_points = []
        elif shape == 'rectangle':
            tmp_point = (x, y)
        elif shape == 'circle':
            tmp_point = Point(x, y)

    elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON): #左鍵拖曳
        
        if shape == 'polygon':
            tmp = tmp_image
            tmp_points.append([x, y])
            cv2.circle(tmp, (x, y), 0, RED, 2)
        elif shape == 'rectangle':
            tmp = tmp_image.copy()
            cv2.rectangle(tmp, tmp_point, (x, y), RED, 2)
        elif shape == 'circle':
            tmp = tmp_image.copy()
            p1 = Point(x, y)
            p2 = tmp_point
            dist = int(p1.getDistance(p2) / 2)
            mid = p1.polarProjection(dist, p1.getAngle(p2))
            cv2.circle(tmp, mid, dist, RED, 2)
        cv2.imshow('image', tmp)

    elif event == cv2.EVENT_LBUTTONUP: #左键释放
        image.update(image.last.copy())
        if shape == 'polygon':
            points = [[int(xy / image.scaling_ratio) for xy in point] for point in tmp_points]
            points = np.array(points, np.int32)
            points = points.reshape((-1,1,2))
            cv2.fillPoly(image.last, [points], GREEN)
        elif shape == 'rectangle':
            cv2.rectangle(image.last, image.originalPoint(tmp_point), image.originalPoint((x, y)), GREEN, cv2.FILLED)
        elif shape == 'circle':
            p1 = image.originalPoint(Point(x, y))
            p2 = image.originalPoint(tmp_point)
            dist = int(p1.getDistance(p2) / 2)
            mid = p1.polarProjection(dist, p1.getAngle(p2))
            cv2.circle(image.last, mid, dist, GREEN, cv2.FILLED)
        image.show()


def read():
    global image
    import tkinter
    import tkinter.filedialog
    root = tkinter.Tk()
    path = tkinter.filedialog.askopenfilename(defaultextension='jpg', filetypes=[('JPEG', '*.jpg'), ('JPEG', '*.jpeg'), ('PNG', '*.png'), ('BMP', '*.bmp')])
    root.destroy()
    if path == '':
        return

    try:
        tmp_image = Image(path)
    except Exception as e:
        print(e)
    image = tmp_image
    image.show()


def output(mode):
    global image, mouse_enabled
    if not image:
        return

    mouse_enabled = False
    path_input = os.path.join(workdir, PATH_INPUT)
    path_input_original = os.path.join(workdir, PATH_INPUT_ORIGINAL)
    path_output = os.path.join(workdir, PATH_OUTPUT)

    cv2.imwrite(os.path.join(path_input, 'tmp.png'), image.last)
    cv2.imwrite(os.path.join(path_input_original, 'tmp.png'), image.first)

    execute = 'decensor.py' if os.path.exists(os.path.join(workdir, 'decensor.py')) else 'decensor.exe'
    command = [
        execute,
        '--decensor_input_path=%s' % path_input,
        '--decensor_input_original_path=%s' % path_input_original,
        '--decensor_output_path=%s' % path_output,
    ]
    if mode == 'bleak':
        print('===== 處理中 (去除海苔條) =====')
    elif mode == 'mosaic':
        print('===== 處理中 (去除馬賽克) =====')
        command.append('--is_mosaic=True')
    import subprocess
    stdout = subprocess.check_output(' '.join(command), shell=True, cwd=workdir)
    print(stdout)

    if os.path.exists(os.path.join(path_output, 'tmp.png')):
        output_image = Image(os.path.join(path_output, 'tmp.png'))
        output_image.show()
        print(TIP2)
        while True:
            key = cv2.waitKey(0)
            if key in [-1, 27]: # 27=esc
                cv2.destroyAllWindows()
                sys.exit(0)
            elif key in [82, 114]: # 82=R 114=r
                read()
            elif key in [69, 101]: # 69=E 101=e
                mouse_enabled = True
                cv2.imshow('image', image.last)
                print(TIP)
                break
            elif key in [83, 115]: #83=S 115=s
                filename, fileext = os.path.splitext(image.path)
                path = os.path.join(os.path.dirname(image.path), '%s_uncensored%s' % (filename, fileext))
                cv2.imwrite(path, output_image.last)
                print('已儲存為: %s' % path)
            else:
                print('%s\n.....沒有命令: %s' % (TIP, key))
    else:
        print('.....失敗')

def main():
    global image, shape
    print(TIP)
    cv2.namedWindow('image')
    cv2.setMouseCallback('image', onMouse)
    image = Image(sys.argv[1] if len(sys.argv) > 1 else './no_image.jpg')
    image.show()
    while True:
        key = cv2.waitKey(0)
        if key in [-1, 27]: # 27=esc
            cv2.destroyAllWindows()
            break
        elif key in [82, 114]: # 82=R 114=r
            read()
        elif key == 26: # 26=ctrl+z
            image.rollback()
        elif key == 49: # 49=num1
            shape = 'polygon'
            print('切換筆刷: 多邊形')
        elif key == 50: # 50=num2
            shape = 'rectangle'
            print('切換筆刷: 矩形')
        elif key == 51: # 51=num3
            shape = 'circle'
            print('切換筆刷: 圓形')
        elif key in [66, 98]: # 66=B 98=b
            output('bleak')
        elif key in [77, 109]: # 77=M 109=m
            output('mosaic')
        else:
            print('%s\n.....沒有命令: %s' % (TIP, key))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import logging
        logger_path = os.path.join(workdir, 'error.log')
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.FileHandler(logger_path, 'w'))
        logger.exception(e)
        try:
            os.system('start "" "%s"' % logger_path)
        except:
            pass
        raise e
