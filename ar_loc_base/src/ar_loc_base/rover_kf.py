import rospy
from numpy import *
from numpy.linalg import pinv, inv
from math import pi, sin, cos
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
import tf
import threading

from ar_loc_base.rover_kinematics import *

class RoverKF(RoverKinematics):
    def __init__(self, initial_pose, initial_uncertainty):
        RoverKinematics.__init__(self)
        self.lock = threading.Lock()
        self.X = mat(vstack(initial_pose))
        self.P = mat(diag(initial_uncertainty))
        self.ellipse_pub = rospy.Publisher("~ellipse",Marker,queue_size=1)
        self.pose_with_cov_pub = rospy.Publisher("~pose_with_covariance",PoseWithCovarianceStamped,queue_size=1)

    def getRotation(self, theta):
        R = mat(zeros((2,2)))
        R[0,0] = cos(theta); R[0,1] = -sin(theta)
        R[1,0] = sin(theta); R[1,1] = cos(theta)
        return R
    
    def predict(self, motor_state, drive_cfg, encoder_precision):
        self.lock.acquire()
        # The first time, we need to initialise the state
        if self.first_run:
            self.motor_state.copy(motor_state)
            self.first_run = False
            self.lock.release()
            return (self.X, self.P)
        # Prepare odometry matrices (check rover_odo.py for usage)
        iW = self.prepare_inversion_matrix(drive_cfg)
        S = self.prepare_displacement_matrix(self.motor_state,motor_state,drive_cfg)
        self.motor_state.copy(motor_state)
        
        # Implement Kalman prediction here
        # TODO
        rot=array([[cos(self.X[2]), -sin(self.X[2]), 0], 
                   [sin(self.X[2]), cos(self.X[2]), 0], 
                   [0, 0, 1]])
        dX=dot(iW,S)
        A=array([[1, 0, -sin(self.X[2])*dX[1,0]-cos(self.X[2])*dX[0,0]], 
                  [0, 1, cos(self.X[2])*dX[0,0]-sin(self.X[2])*dX[1,0]], 
                  [0, 0, 1]])
        tA=transpose(A)
        B=dot(rot,iW)
        tB=transpose(B)
        Qu=eye(12)*(encoder_precision**2)
        Q=eye(3)*1e-6

        self.X=self.X+dot(dot(rot,iW),S)
        self.P=mat(dot(dot(A,self.P),tA)+dot(dot(B,Qu),tB)+Q)

        self.lock.release()
        return (self.X,self.P)

    def update_ar(self, Z, L, uncertainty):
        self.lock.acquire()
        print("Update: L="+str(L.T)+" X="+str(self.X.T))
        # Implement kalman update using landmarks here
        # TODO
        X2=self.X[:2]
        dL=L-X2
        H=array([[-cos(self.X[2]), -sin(self.X[2]), -dL[0,0]*sin(self.X[2])+dL[1,0]*cos(self.X[2])], 
                  [sin(self.X[2]), -cos(self.X[2]), -dL[0,0]*cos(self.X[2])-dL[1,0]*sin(self.X[2])]])
        tH=transpose(H)
        R=eye(2)*uncertainty
        K=dot(dot(self.P,tH),inv(dot(dot(H,self.P),tH)+R))
        I=identity(3)
        rotM=array([[cos(self.X[2]), sin(self.X[2])], [-sin(self.X[2]), cos(self.X[2])]])
        h=dot(rotM,(L-X2))
        self.X = self.X+dot(K,Z-h)
        self.P = dot((I-dot(K,H)),self.P)
        self.lock.release()
        return (self.X,self.P)

    def update_compass(self, Z, uncertainty):
        self.lock.acquire()
        print("Update: S="+str(Z)+" X="+str(self.X.T))
        # Implement kalman update using compass here
        # TODO
        # self.X = 
        # self.P = 
        self.lock.release()
        return 

    # this publishes the pose but also the pose with covariance and the error ellipse in rviz
    def publish(self, pose_pub, target_frame, stamp):
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = target_frame
        pose.header.stamp = stamp
        pose.pose.pose.position.x = self.X[0,0]
        pose.pose.pose.position.y = self.X[1,0]
        pose.pose.pose.position.z = 0.0
        Q = tf.transformations.quaternion_from_euler(0, 0, self.X[2,0])
        pose.pose.pose.orientation.x = Q[0]
        pose.pose.pose.orientation.y = Q[1]
        pose.pose.pose.orientation.z = Q[2]
        pose.pose.pose.orientation.w = Q[3]
        psub = PoseStamped()
        psub.header = pose.header
        psub.pose = pose.pose.pose
        pose_pub.publish(psub)
        C = [0]*36
        C[ 0] = self.P[0,0]; C[ 1] = self.P[0,1]; C[ 5] = self.P[0,2]
        C[ 6] = self.P[1,0]; C[ 7] = self.P[1,1]; C[11] = self.P[1,2]
        C[30] = self.P[2,0]; C[31] = self.P[2,1]; C[35] = self.P[2,2]
        pose.pose.covariance = C
        self.pose_with_cov_pub.publish(pose)
        marker = Marker()
        marker.header = pose.header
        marker.ns = "kf_uncertainty"
        marker.id = 1
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.pose = pose.pose.pose
        marker.scale.x = 3*sqrt(self.P[0,0])
        marker.scale.y = 3*sqrt(self.P[1,1]);
        marker.scale.z = 0.1;
        marker.color.a = 1.0;
        marker.color.r = 1.0;
        marker.color.g = 1.0;
        marker.color.b = 0.0;
        self.ellipse_pub.publish(marker)

    # broadcast the estimated transform
    def broadcast(self,br, target_frame, stamp):
        br.sendTransform((self.X[0,0], self.X[1,0], 0),
                     tf.transformations.quaternion_from_euler(0, 0, self.X[2,0]),
                     stamp, "/%s/ground"%self.name, target_frame)
        

