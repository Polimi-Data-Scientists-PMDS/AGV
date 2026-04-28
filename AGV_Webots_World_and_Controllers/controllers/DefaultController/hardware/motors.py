from control.control import ControlCommand
from config import PhysicalConfig

class Motors:
    """Handles the motors, encoders, and wheel velocities."""
    def __init__(self, robot, timestep):
        self.config = PhysicalConfig()
        self.motorL = robot.getDevice('left wheel motor')
        self.motorR = robot.getDevice('right wheel motor')
        self.motorL.setPosition(float('inf'))
        self.motorR.setPosition(float('inf'))
        
        self.posL = self.motorL.getPositionSensor()
        self.posR = self.motorR.getPositionSensor()
        self.posL.enable(timestep)
        self.posR.enable(timestep)
        
        self.prevL, self.prevR = 0.0, 0.0
        print("Motors and encoders set up correctly!")

    def get_deltas(self):
        curr_L = self.posL.getValue()
        curr_R = self.posR.getValue()
        dL = curr_L - self.prevL
        dR = curr_R - self.prevR
        self.prevL, self.prevR = curr_L, curr_R
        return dL, dR

    def apply_command(self, command:ControlCommand):
        w_l, w_r = command.w_l, command.w_r
        self.motorL.setVelocity(w_l)
        self.motorR.setVelocity(w_r)

    def get_velocities(self):
        w_r = self.motorR.getVelocity()
        w_l = self.motorL.getVelocity()
        v_r = w_r * self.config.wheel_radius
        v_l = w_l * self.config.wheel_radius
        return v_l, v_r

    def stop(self):
        self.motorL.setVelocity(0.0)
        self.motorR.setVelocity(0.0)