import cv2


class FaceDetector:

    def __init__(self):
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            "haarcascade_frontalface_default.xml"
        )

    def detect(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=6,
            minSize=(120,120)
        )

        if len(faces) == 0:
            return None

        # largest face
        return max(faces, key=lambda f: f[2] * f[3])