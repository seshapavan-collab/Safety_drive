import cv2
import numpy as np


def get_head_pose(lms, w, h):
    """
    lms: List of tuples [(x, y), (x, y), ...]
    w: frame width
    h: frame height
    """
    face_2d = []
    face_3d = []

    # Standard 3D model points (Nose, Eyes, Mouth corners, Chin)
    indices = [1, 33, 263, 61, 291, 199]

    for idx in indices:
        # lms[idx] is a tuple (x, y)
        lm = lms[idx]

        # Access by index since it's a tuple
        x, y = int(lm[0] * w), int(lm[1] * h)

        face_2d.append([x, y])
        face_3d.append([x, y, 0])

    face_2d = np.array(face_2d, dtype=np.float64)
    face_3d = np.array(face_3d, dtype=np.float64)

    focal_length = 1 * w
    cam_matrix = np.array([[focal_length, 0, h / 2],
                           [0, focal_length, w / 2],
                           [0, 0, 1]])

    dist_matrix = np.zeros((4, 1), dtype=np.float64)

    # Solve PnP
    success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)

    # Get Rotation Matrix
    rmat, jac = cv2.Rodrigues(rot_vec)

    # Manual Euler Extraction
    sy = np.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
    singular = sy < 1e-6

    if not singular:
        x = np.arctan2(rmat[2, 1], rmat[2, 2])
        y = np.arctan2(-rmat[2, 0], sy)
    else:
        x = np.arctan2(-rmat[1, 2], rmat[1, 1])
        y = np.arctan2(-rmat[2, 0], sy)

    # Convert to degrees
    pitch = np.degrees(x)
    yaw = np.degrees(y)

    return pitch, yaw