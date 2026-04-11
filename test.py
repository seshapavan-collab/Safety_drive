import cv2

# Initialize webcam
cap = cv2.VideoCapture(0)

print("Press 'q' to exit the test")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Camera not found!")
        break

    cv2.imshow("GuardianDrive Setup Check", frame)

    # Exit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()