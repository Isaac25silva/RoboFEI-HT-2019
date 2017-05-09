__author__ = "RoboFEI-HT"
__authors__ = "Aislan C. Almeida"
__license__ = "GNU General Public License v3.0"

import numpy as np
import scipy.special as sp

# Robot's height!!!
hrobot = 50
# Robot's head's tilt's position
htilt = 17.4

# Distance and angles of the notable points
vpoints = [(1030,20),
           (880,20),
           (740,20),
           (600,20),
           (450,20),
           (310,20),
           (170,20),

           (990,-20),
           (850,-20),
           (710,-20),
           (560,-20),
           (420,-20),
           (280,-20),
           (130,-20),

           (910,10),
           (780,10),
           (640,10),
           (500,10),
           (370,10),
           (230,10),

           (880,-10),
           (750,-10),
           (610,-10),
           (470,-10),
           (330,-10),
           (190,-10),
           
           (1000,0),
           (160,0),
           (90,0)]

# Vars used to compute the particles likelihood
maxWdelta = None

#--------------------------------------------------------------------------------------------------
#   Class implementing a particle used on Particle Filter Localization
#--------------------------------------------------------------------------------------------------

class Particle(object):
    #----------------------------------------------------------------------------------------------
    #   Particle constructor
    #----------------------------------------------------------------------------------------------
    def __init__(self, x=None, y=None, rotation=None, weight=1, maxweight=1, normals=None, regions=None, factors=None, std=None, spread=1):
        # This block sets the initial position values of the particles.
        #    If there was any given value, adopt it;
        #    else if there was a gaussian possible position given, generate a random position;
        #    else create a totally random one.

        # Note: normals is a 3x2 matrix, where
        #    the first line presents the mean and standard deviation of the x position
        #    the second line presents the mean and standard deviation of the y position
        #    the third line presents the mean and standard deviation of the rotation

        # Note2: regions is a 3x2 matrix, where
        #    the first line presents the min and max values of the x position
        #    the second line presents the min and max values of the y position
        #    the third line presents the min and max values of the rotation

        # Note3: factors are the factors for the motion model of the particles

        # Note4: std is a vector with the values used as standard deviation for computing particles' likelihood.
        #    the first for is used for the landmarks, in sequence blue, red, yellow, purple
        #    the last one is used for the IMU orientation

        # Note5: spread determines how much the particles will spread

        if regions == None:
            regions = ((0, 1040), (0, 740), (-180, 180))

        if x != None:
            self.x = x
        elif normals:
            self.x = np.random.normal(normals[0][0], normals[0][1])
        else:
            self.x = np.random.randint(regions[0][0], regions[0][1])

        if y != None:
            self.y = y
        elif normals:
            self.y = np.random.normal(normals[1][0], normals[1][1])
        else:
            self.y = np.random.randint(regions[1][0], regions[1][1])

        if rotation != None:
            self.rotation = rotation
        elif normals:
            self.rotation = np.random.normal(normals[2][0], normals[2][1])
        else:
            self.rotation = np.random.randint(regions[2][0], regions[2][1])
        
        self.weight = weight # Holds particles weight, can come from previous iterations
        self.maxweight = maxweight # Holds the previous maximum weight

        # Motion error coefficients
        if factors == None:
            self.factors = [1, 2, 1, 500, 1,  1, 2, 1, 500, 1.5,  1, 2, 1, 100, 1]
            # self.factors = 15*[0]
            # self.factors = [1, 2, 1, 0, 10,  1, 2, 1, 0, 20,  1, 2, 1, 0, 10]
            # self.factors = [0, 0, 0, 0, 10,  0, 0, 0, 0, 20,  0, 0, 0, 0, 10]
        else:
            self.factors = factors

        # Standard deviation used for computing angles likelihoods, in degrees.
        if std == None:
            self.std = [5, 30]
        else:
            self.std == std

        # Vars used to compute the particles likelihood
        self.gamma = 26.13
        self.Delta = 90

        self.psi = 0.7
        self.SigmaO = 70
        self.MuF = 700
        self.SigmaF = 10
        self.MuN = 10
        self.SigmaN = 1

        self.SigmaA = 5

        self.radius = (10,50)

        self.SigmaIMU = 20

    #----------------------------------------------------------------------------------------------
    #   Method that chooses which movement should be used
    #----------------------------------------------------------------------------------------------
    def Movement(self, straight=0, drift=0, rotational=0, moving=1, dt=0):
        if moving == 1:
            self.Motion(straight, drift, rotational, dt)
        elif moving == 2:
            self.GetUpBackUp()
        elif moving == 3:
            self.GetUpFrontUp()
        else:
            self.Motion(0,0,0,dt)

    #----------------------------------------------------------------------------------------------
    #   Method which moves particles around, reimplement.
    #----------------------------------------------------------------------------------------------
    def Motion(self, straight=0, drift=0, rotational=0, dt=0):
        # straight is the robot's forward speed in cm/s
        # drift is the robot's sideways speed in cm/s
        # rotational is the robot's angular speed in degrees/s

        wfactor = max(min(np.log(self.weight/self.maxweight)/np.log(1e-20), 1.), 0.)

        # Computes the forward speed with error
        Forward = straight + NRnd(self.factors[0]*straight) + NRnd(self.factors[1]*drift) + NRnd(self.factors[2]*rotational) + NRnd(self.factors[3] * wfactor)/dt + NRnd(self.factors[4])/dt
        # Computes the side speed with error
        Side = drift + NRnd(self.factors[5]*straight) + NRnd(self.factors[6]*drift) + NRnd(self.factors[7]*rotational) + NRnd(self.factors[8] * wfactor)/dt + NRnd(self.factors[9])/dt
        # Computes the angular speed with error
        Omega = rotational + NRnd(self.factors[10]*straight) + NRnd(self.factors[11]*drift) + NRnd(self.factors[12]*rotational) + NRnd(self.factors[13] * wfactor)/dt + NRnd(self.factors[14])/dt

        # Converts angles to radians
        Omega = np.radians(Omega)
        Theta = np.radians(self.rotation)

        # Computes the new positions
        if Omega == 0:
            Direction = Theta
            x = self.x + Forward * np.cos(Theta) * dt + Side * np.sin(Theta) * dt
            y = self.y - Forward * np.sin(Theta) * dt + Side * np.cos(Theta) * dt
        else:
            Direction = Theta + Omega * dt
            Dir2 = -Theta + Omega * dt
            x = self.x + Forward/Omega * (np.sin(Direction)-np.sin(Theta)) - Side/Omega * (np.cos(-Theta)-np.cos(Dir2))
            y = self.y - Forward/Omega * (np.cos(Theta)-np.cos(Direction)) - Side/Omega * (np.sin(-Theta)-np.sin(Dir2))

        if x < 0 or x > 1040 or y < 0 or y > 740:
            return 


        # Saves the new positions
        self.x = x
        self.y = y
        rot = np.degrees(Direction)
        if rot > 180:
            self.rotation = rot - 360
        elif rot < -180:
            self.rotation = rot + 360
        else:
            self.rotation = rot

        # Resets weight variables
        self.weight = 1
        self.maxweight = 1

    #----------------------------------------------------------------------------------------------
    #   Method to replace particles after rising up
    #----------------------------------------------------------------------------------------------
    def GetUpBackUp(self):
        self.x += NRnd(7)
        self.y += NRnd(7)
        self.rotation += NRnd(25)

    #----------------------------------------------------------------------------------------------
    #   Method which replaces particles after turning on the ground
    #----------------------------------------------------------------------------------------------
    def GetUpFrontUp(self):
        self.x += NRnd(7,-30)*np.sin(np.radians(self.rotation))
        self.y += NRnd(7,-30)*np.cos(np.radians(self.rotation))
        self.rotation += NRnd(25)
        self.GetUpBackUp()

    #----------------------------------------------------------------------------------------------
    #   Likelihood computation
    #----------------------------------------------------------------------------------------------
    def Sensor(self, landmarks=None, field=None, orientation=None, weight=1):
        # If it was given landmarks
        if landmarks != None:
            # Computes the landmarks positions
            lm = []

            # print
            for z in [(70,280), (70,460), (970,280), (970,460)]:
                dx = z[0]-self.x
                dy = z[1]-self.y

                dist = np.hypot(dx, dy)
                ang = -np.degrees(np.arctan2(dy, dx))-self.rotation

                lm.append([dist, ang])

            # Computes weights using the formulas from the text
            for z in landmarks:
                
                # print "-----------"

                # aux weight vectors
                w = len(lm)*[1]

                # try each landmark
                for i in range(len(lm)):
                    if z != -999:
                        w[i] *= Wdelta(lm[i][0], self.psi, self.SigmaO, self.MuF, self.SigmaF, self.MuN, self.SigmaN)
                        w[i] *= ComputeAngLikelihoodDeg(lm[i][1], z, self.SigmaA)
                    # else:
                    #     w[i] = 1 - Walpha(lm[i][1], self.gamma, self.Delta)
                    #     w[i] += 1 - Wdelta(lm[i][0], self.psi, self.SigmaO, self.MuF, self.SigmaF, self.MuN, self.SigmaN)
                    #     w[i] /= 2.
                    # else:
                    #     w[i] *= 1-Walpha(lm[i][1], self.gamma, self.Delta)
                    #     w[i] *= 1-Wdelta(lm[i][0], self.psi, self.SigmaO, self.MuF, self.SigmaF, self.MuN, self.SigmaN)

                    # print "real:", z, "virtual:", lm[i]
                    # print "weight:", w[i]

                    # aux = 1
                    # W alpha
                    # if z == -999:
                    #     aux = 1 - Walpha(lm[i][1], self.gamma, self.Delta)
                    #     w[i] *= aux
                    # else:
                        # aux = Walpha(lm[i][1], self.gamma, self.Delta)
                        # w[i] *= aux

                    # print "weight:", aux, "x",

                    # # W delta
                    # if z == -999:
                    #     aux = 1 - Wdelta(lm[i][0], self.psi, self.SigmaO, self.MuF, self.SigmaF, self.MuN, self.SigmaN)
                    #     w[i] *= aux
                    # else:
                    #     aux = Wdelta(lm[i][0], self.psi, self.SigmaO, self.MuF, self.SigmaF, self.MuN, self.SigmaN)
                    #     w[i] *= aux

                    # print aux, "x",

                    # W phi
                    # if z != -999:
                    #     aux = ComputeAngLikelihoodDeg(lm[i][1], z, self.SigmaA)
                    #     w[i] *= aux

                    # print aux

                    # print

                weight *= max(w) # Maximizes the weight
                lm.pop(w.index(max(w))) # Erases the used landmark
            # print "-----------"
            # print "final:", self, ">>", weight
            # print "-----------"
            # print
            # exit()

        # If the given information is the field's points
        if field != None:
            # Finds out the head's position
            if field[0:3] == [1,1,1]:
                pan = 90
            elif field[0:3] == [1,1,0]:
                pan = -90
            elif field[0:3] == [1,0,1]:
                pan = 60
            elif field[0:3] == [1,0,0]:
                pan = -60
            elif field[0:3] == [0,1,1]:
                pan = 30
            elif field[0:3] == [0,1,0]:
                pan = -30
            else:
                pan = 0

            ret = [] # Holds the probabilities of each point been 1
            for k in vpoints:
                p = np.radians(-self.rotation + pan + k[1]) # Computes the direction
                i = self.x + k[0] * np.cos(p) # Computes the x position of the point
                j = self.y + k[0] * np.sin(p) # Computes the y position of the point

                ret.append(prob(i, j, self.radius, k[0])) # Computes the probability of the point been inside the field

            # Computes a normalization value
            n = 1
            for i in xrange(3, 32):
                n *= 0.99 * field[i] + 0.9 * (1-field[i])

            # Computes the normalized weight
            w = 1
            for i in xrange(3, 32):
                w *= 0.99 * field[i] * ret[i-3] + 0.9 * (1-field[i]) * (1-ret[i-3]) + 0.2 * field[i] * (1-ret[i-3]) + 0.1 * (1-field[i]) * ret[i-3]
            
            w /= n
        
            weight *= w

        # If the IMU's orientation was given
        if orientation != None:
            weight *= ComputeAngLikelihoodDeg(np.degrees(orientation), self.rotation, self.SigmaIMU)
        
        self.weight = max(weight, 1e-300)
        return self.weight
        
    #----------------------------------------------------------------------------------------------
    #   Computes the max weight of the particles, generally 1.
    #----------------------------------------------------------------------------------------------
    def MaxWeight(self, landmarks=None, field=None, orientation=None):
        weight = 1
        if landmarks != None:
            for lm in landmarks:
                if lm != -999:
                    weight *= Walpha(0)
                    weight *= maxWdelta
                else:
                    weight *= 1 - Walpha(0)

        return max(weight, 1e-300)

    #----------------------------------------------------------------------------------------------
    #   Returns a string to print the particle's representation.
    #----------------------------------------------------------------------------------------------
    def __repr__(self):
        return "x: " + str(self.x) + " y: " + str(self.y) + " z: " + str(self.rotation) + " w: " + str(self.weight)

    #----------------------------------------------------------------------------------------------
    #   Returns the variables used to create a new particle from this one.
    #----------------------------------------------------------------------------------------------
    def copy(self):
        return self.x, self.y, self.rotation, self.weight

#--------------------------------------------------------------------------------------------------
#   Computes the likelihood between two angles in degrees.
#--------------------------------------------------------------------------------------------------
def ComputeAngLikelihoodDeg(ang, base, std_deviation=0):
    # Note: the standard deviation also is in degrees

    # If the standard deviation is null
    if std_deviation == 0: 
        # return a binary answer.
        if ang == base:
            return 1
        else:
            return 0
    else:
        # else computes the Cartesian points based on the angles,
        xa = np.cos(np.radians(ang))
        ya = np.sin(np.radians(ang))
        xb = np.cos(np.radians(base))
        yb = np.sin(np.radians(base))

        # computes the distance between these points,
        d = np.hypot(xa-xb, ya-yb)

        # converts the standard deviation into aa distance measure,
        sa = np.cos(np.radians(std_deviation))
        sb = np.sin(np.radians(std_deviation))
        s = np.hypot(sa-1, sb)

        # returns the likelihood between the given angles.
        return np.exp(-np.power(d,2)/(2*np.power(s,2)))

#--------------------------------------------------------------------------------------------------
#   Returns a random number from a normal distribution.
#--------------------------------------------------------------------------------------------------
def NRnd(sigma, mu=0):
    if sigma == 0:
        return mu
    else:
        return np.random.normal(mu, np.abs(sigma))

#--------------------------------------------------------------------------------------------------
#   Returns the probability given the x and y limits, the circle position and its radius.
#--------------------------------------------------------------------------------------------------
def prob(cx, cy, rad, d, xa=0, xb=1040, ya=0, yb=740):
    w = 1 # Default

    # Computes the radius used to compute the weight of this set of points
    r = (rad[1]-rad[0])*d/900. + 10.*rad[0]/9. - rad[1]/9. 

    # Computes the integral of the field in relation to the field (Too complex to be explained here, just believe it!)
    if cx+r <= xa or cx-r >= xb:
        return 0
    elif cx-r < xa:
        w *= 0.5 - ((xa-cx)*np.sqrt((r**2)-(xa-cx)**2) + (r**2)*np.arctan((xa-cx)/(np.sqrt((r**2)-(xa-cx)**2))))/((r**2)*np.pi)
    elif cx+r > xb:
        w *= 0.5 + ((xb-cx)*np.sqrt((r**2)-(xb-cx)**2) + (r**2)*np.arctan((xb-cx)/(np.sqrt((r**2)-(xb-cx)**2))))/((r**2)*np.pi)

    if cy+r <= ya or cy-r >= yb:
        return 0
    elif cy-r < ya:
        w *= 0.5 - ((ya-cy)*np.sqrt((r**2)-(ya-cy)**2) + (r**2)*np.arctan((ya-cy)/(np.sqrt((r**2)-(ya-cy)**2))))/((r**2)*np.pi)
    elif cy+r > yb:
        w *= 0.5 + ((yb-cy)*np.sqrt((r**2)-(yb-cy)**2) + (r**2)*np.arctan((yb-cy)/(np.sqrt((r**2)-(yb-cy)**2))))/((r**2)*np.pi)

    return w

#--------------------------------------------------------------------------------------------------
#   Computes the Walpha factor for weight computation
#--------------------------------------------------------------------------------------------------
def Walpha(ang, gamma=26.13, Delta=90):
    if -Delta+gamma < ang and ang < Delta-gamma:
        return gamma/(Delta+gamma)
    elif ang < -Delta-gamma or ang > Delta+gamma:
        return 0
    else:
        return 0.5 * (Delta+gamma-np.abs(ang))/(Delta+gamma)

#--------------------------------------------------------------------------------------------------
#   Computes the Wdelta factor for weight computation
#--------------------------------------------------------------------------------------------------
def Wdelta(dist, psi=0.7, SigmaO=70, MuF=700, SigmaF=10, MuN=10, SigmaN=1):
    return (psi + (1-psi)*np.exp(-np.power(dist,2)/(2*np.power(SigmaO,2)))) * (1 + sp.erf((MuF-dist)/(np.sqrt(2)*SigmaF))) * (1 - sp.erf((MuN-dist)/(np.sqrt(2)*SigmaN))) / 4

#--------------------------------------------------------------------------------------------------
#   Computes the maximum value Wdelta can get.
#--------------------------------------------------------------------------------------------------
if maxWdelta == None:
    psi = 0.7 # Occlusion factor in the infinity
    SigmaO = 70 # Decay rate of the occlusion factor
    
    MuF = 700 # Farthest distance in which a robot can see any landmark
    SigmaF = 10 # Its decay rate
    
    MuN = 10 # Nearest distance a robot can see anything
    SigmaN = 1 # Its decay rate

    # Generates a 1000 points in random positions
    d = np.array([]) 
    for i in xrange(1000):
        d = np.append(d, [np.random.randint(MuN, MuF)])

    w = 0 # Initializes the weight as 0
    while True:
        p = w # Saves the prev. weight

        d = np.random.normal(d, 0.3) # Moves points at random
        e = Wdelta(d) # Computes the new vector of weights

        w = np.max(e) # Get the biggest weight

        if np.abs(w-p) < 1e-3: # If it was just a small change saves it
            d = d[np.argmax(e)]
            break

    maxWdelta = Wdelta(d) # Saves the greatest weight