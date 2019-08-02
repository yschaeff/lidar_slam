import cv2
import matplotlib.pyplot as plt
import numpy as np

image1 = cv2.imread('face1.jpeg')
training_image = cv2.cvtColor(image1, cv2.COLOR_BGR2RGB)
training_gray = cv2.cvtColor(training_image, cv2.COLOR_RGB2GRAY)

orb = cv2.ORB_create()
train_keypoints, train_descriptor = orb.detectAndCompute(training_gray, None)
keypoints_with_size = np.copy(training_image)
cv2.drawKeypoints(training_image, train_keypoints, keypoints_with_size, flags = cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

fx, plots = plt.subplots()
plots.imshow(keypoints_with_size, cmap='gray')
plt.show()
