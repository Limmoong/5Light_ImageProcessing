import argparse
import logging  # 디버그할 때 로그찍어주는 모듈
import cv2  # opencv 모듈
import numpy as np
import imutils
import math
from ImageProcessing_py import utils

if __name__ == '__main__':  # 플러그
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video_path', type=str, help="paths to one or more images or image directories")
    parser.add_argument('-b', '--debug', dest='debug', action='store_true', help='enable debug logging')
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='disable all logging')
    parser.add_argument('-d', '--display', dest='display', action='store_true', help="display result")
    parser.add_argument('-s', '--save', dest='save', action='store_true', help="save result to file")
    parser.add_argument("--save_path", dest='save_path', default="stitched.png", type=str, help="path to save result")
    parser.add_argument('-k', '--knn', dest='knn', default=2, type=int, help="Knn cluster value")
    parser.add_argument('-l', '--lowe', dest='lowe', default=0.7, type=float, help='acceptable distance between points')
    parser.add_argument('-m', '--min', dest='min_correspondence', default=10, type=int, help='min correspondences')
    args = parser.parse_args()

    if args.debug:  # 예외처리
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("main")

    logging.info("beginning sequential matching")

    if utils.helpers.is_cv2():  # opencv 버전 별
         sift = cv2.SIFT()
    elif utils.helpers.is_cv3():
         sift = cv2.xfeatures2d.SIFT_create()
    elif utils.helpers.is_cv4():
         sift = cv2.SIFT_create()
    else:
         raise RuntimeError("error! unknown version of python!")

    result = None
    result_gry = None
    result_preview = None
    warped_img = None

    flann = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 50})

    cap = cv2.VideoCapture(args.video_path)
    beforeResult = cv2.imread("res/panorama/0511sam/result4.jpg")
    beforeResult_gray = cv2.cvtColor(beforeResult, cv2.COLOR_BGR2GRAY)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("length : ", length)
    print("width : ", width)
    print("height : ", height)
    print("fps : ", fps)
    i = 0
    resultT = None
    features1 = None
    meanTime = 0
    j = 0
    h, w, f = 405, 720, 950
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], dtype=np.float32)
    angles = math.pi / 180
    theta = [angles * 0, angles * 45, angles * 45]
    R = utils.helpers.eulerAnglesToRotationMatrix(theta)

    while True:
        ret, frame = cap.read()
        if i % 4 != 0:
            i = i + 1
            continue
        i = i + 1

        if not ret:  # 제대로 못읽었을 경우
            break
        else:  # 제대로 읽었을 경우 그레이로 바꾸기
            if frame.shape[1] > 720:
                frame = imutils.resize(frame, width=720)

            warper = cv2.PyRotationWarper('spherical', float(f))
            corner, frame = warper.warp(frame, K, R, cv2.INTER_CUBIC, cv2.BORDER_CONSTANT)
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            features0 = sift.detectAndCompute(frame_gray, None)
            if features1 is None:
                features1 = sift.detectAndCompute(beforeResult_gray, None)

            matches_src, matches_dst, n_matches = utils.compute_matches(
                features0, features1, flann, knn=args.knn)

            if n_matches < args.min_correspondence:
                logger.error("error! too few correspondences")
                continue

            H, mask = cv2.findHomography(matches_src, matches_dst, cv2.RANSAC, 5.0)

            if resultT is None:
                h0, w0 = beforeResult.shape[0:2]
                resultT = np.zeros((h0, w0, 3), np.uint8)
            resultT, blendTime = utils.combine_images(beforeResult, frame, H, resultT)

    logger.info('{0} is completed'.format(args.video_path))
    cap.release()
    cv2.destroyAllWindows()
    if args.save:
        utils.helpers.save_image(args.video_path, resultT)