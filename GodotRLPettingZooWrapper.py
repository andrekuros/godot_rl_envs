from godot_rl.core.godot_env import GodotEnv
from pettingzoo.utils import ParallelEnv

from godot_rl.core.utils import ActionSpaceProcessor, convert_macos_path
import numpy as np
import gymnasium as gym
import torch
import atexit
from sys import platform
from gymnasium import spaces
import json
import subprocess
from typing import Optional


class GodotRLPettingZooWrapper(GodotEnv, ParallelEnv):
    metadata = {'render.modes': [], 'name': "godot_rl_multi_agent"}

    def __init__(self,
                env_path: str = None,
                port: int = GodotEnv.DEFAULT_PORT,
                show_window: bool = True,
                seed: int = 0,
                framerate: Optional[int] = None,
                action_repeat: Optional[int] = None,
                speedup: Optional[int] = None,
                convert_action_space: bool = False,
                **env_config_kwargs):
                       
        #super().__init__( **kwargs)

        # Assuming env_config_kwargs is a dictionary with all necessary keys and values
        #env_path = env_config_kwargs.pop("env_path", "BVR_AirCombat/bin/BVR_1x1_FullView.exe")
        num_agents = env_config_kwargs.pop("num_allies", 1)
        num_enemies = env_config_kwargs.pop("num_enemies", 1)
        #show_window = env_config_kwargs.pop("show_window", False)
        #seed = env_config_kwargs.pop("seed", 0)
        #port = env_config_kwargs.pop("port", 12500)
        #framerate = env_config_kwargs.pop("framerate", None)
        #action_repeat = env_config_kwargs.pop("action_repeat", 20)
        action_type = env_config_kwargs.pop("action_type", "Low_Level_Continuous")
        #speedup = env_config_kwargs.pop("speedup", 2000)

        self.proc = None
        if env_path is not None and env_path != "debug":
            env_path = self._set_platform_suffix(env_path)

            self.check_platform(env_path)  

            self._launch_env(env_path, port, show_window, framerate, seed, action_repeat, speedup,
                             num_agents, num_enemies, action_type)
        else:
            print("No game binary has been provided, please press PLAY in the Godot editor")

        self.port = port
        self.connection = self._start_server()
        self.num_envs = None
        self._handshake()
        self._get_env_info()
        # sf2 requires a tuple action space
        self._tuple_action_space = spaces.Tuple([v for _, v in self._action_space.items()])
        self.action_space_processor = ActionSpaceProcessor(self._tuple_action_space, convert_action_space)

        atexit.register(self._close)

        #Initialization for PettingZoo Paralell
        self.agents = [f'agent_{i}' for i in range(num_agents)]  # Initialize agents
        self.possible_agents = self.agents[:]

        self.action_type = action_type
        
        self.agent_idx = [ {agent : i} for i, agent in enumerate(self.possible_agents)]
                
        # Initialize observation and action spaces for each agent
        self.observation_spaces = {agent: self._observation_space['observation'] for agent in self.agents}
        self.action_spaces = {agent: self.action_space for agent in self.agents}

        print(self.action_spaces)
        
        # self.observation_space = self._observation_space
        # self.action_space = self._action_space
        
        self._cumulative_rewards = {agent : 0  for agent in self.possible_agents}                
        self.rewards =  {agent : 0  for agent in self.possible_agents}
        self.terminations =  {agent : False  for agent in self.possible_agents}
        self.truncations =  {agent : False  for agent in self.possible_agents} 
        self.observations =  {agent : {}  for agent in self.possible_agents}  
        self.info =  {agent : {}  for agent in self.possible_agents}  


    def _launch_env(self, env_path, port, show_window, framerate, seed, action_repeat, speedup, 
                    num_agents, num_enemies, action_type):        
                
        # --fixed-fps {framerate}
        path = convert_macos_path(env_path) if platform == "darwin" else env_path

        launch_cmd = f"{path} --port={port} --env_seed={seed}"

        # Building the launch command
        launch_cmd = f"{env_path}"

        # Adding parameters to the command string based on the extracted values
        launch_cmd += f" --num_allies={num_agents}"
        launch_cmd += f" --num_enemies={num_enemies}"
        if not show_window:
            launch_cmd += " --disable-render-loop --headless"
        if seed is not None:
            launch_cmd += f" --seed={seed}"
        if port is not None:
            launch_cmd += f" --port={port}"
        if framerate is not None:
            launch_cmd += f" --fixed-fps {framerate}"
        launch_cmd += f" --action_repeat={action_repeat}"
        launch_cmd += f" --action_type={action_type}"
        launch_cmd += f" --speedup={speedup}"

        launch_cmd = launch_cmd.split(" ")
        self.proc = subprocess.Popen(
            launch_cmd,
            start_new_session=True,
            # shell=True,
        )
    
    def reset(self, seed=0, options = None):
        
        result  = super().reset()
        
        observations = []
        self.observations = {}

        for i, indiv_obs in enumerate(result[0]):
            # self.observations[self.possible_agents[i]] = { "observation" : torch.tensor(indiv_obs['obs']).to('cuda') }
            # self.observations[self.possible_agents[i]] = np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]).astype(np.float32)#np.array(indiv_obs['observation']).astype(np.float32)
            self.observations[self.possible_agents[i]] =  indiv_obs["observation"] 
            # observations.append(indiv_obs['observation'])
            self.info[self.possible_agents[i]] = {}
            
        # observations =   {'agent_0':  np.array([ 0.        ,  0.        ,  0.52255476,  0.8312247 , -1.4231853 ,
        # -0.4940913 , -1.1777982 , -0.00508968, -0.22760977,  0.10361672,
        # -0.4955089 , -0.27061597,  0.4041192 , -0.00955313,  0.   ]).astype(np.float32), 'agent_1':  np.array([ 0.        ,  0.        ,  0.02704582,  0.5606087 , -0.92767644,
        # -0.22347532, -0.68228924,  0.2655263 ,  0.26789916,  0.37423268,  0.        ,      0.        ,  0.        ,  0.        ]).astype(np.float32)}
        # # self.observations =  {agent :  { }  for agent in self.possible_agents}  
               
        
        # Assuming the reset method returns a dictionary of observations for each agent
        return self.observations, self.info
    
    def observation_space(self, agent):
         return self.observation_spaces[agent]
  
    # def _action_space(self, agent=None):
    #      if agent == None:
    #          return self.action_spaces.values()[0]
    #      return self.action_spaces[agent]


    def action_space(self, agent = None):
        
        return self.action_space_processor.action_space
    
    
    
    def step(self, actions):
        # Assuming the environment's step function can handle a dictionary of actions for each agent
                                       
        if self.action_type == "Low_Level_Continuous":
            godot_actions = [np.array([action]) for agent, action in actions.items()]        
        elif self.action_type == "Low_Level_Discrete": 
            godot_actions = [ self.decode_action(action) for agent, action in actions.items()]
        else:
            print("GododtPZWrapper::Error:: Unknow Actions Type -> ", self.actions_type)
                                
        obs, reward, dones, truncs, info = super().step(godot_actions, order_ij=True)
        
        # Assuming 'obs' is a list of dictionaries with 'obs' keys among others
        for i, agent in enumerate(self.possible_agents):
            # Convert observations, rewards, etc., to tensors
            # .to('cuda') moves the tensor to GPU if you're using CUDA; remove it if not using GPU
            self.observations[agent] =  obs[i]['observation']
            # self.observations[agent] = {torch.tensor(obs[i]['obs'], dtype=torch.float32).to('cuda')}
            self.rewards[agent] = reward[i],#torch.tensor([reward[i]], dtype=torch.float32).to('cuda')
            self.terminations[agent] = dones[i],#torch.tensor([False], dtype=torch.bool).to('cuda')  # Assuming False for all
            self.truncations[agent] = truncs[i],#torch.tensor([False], dtype=torch.bool).to('cuda')  # Assuming False for all
            # For 'info', it might not need to be a tensor depending on its use
            self.info[agent] = info[i]  # Assuming 'info' does not need tensor conversion

        #  # Update the list of active agents based on the 'dones' information
        #  for agent, done in dones.items():
        #      if done:
        #          self.agents.remove(agent)

        # print(self.rewards, dones)
        # print(self.observations)
        return self.observations, self.rewards, self.terminations, self.truncations, self.info 
    
    def last(self, env=None):
        
        """Return the last observations, rewards, and done status."""                        
        return (
            self.observations,
            self.rewards,
            self.terminations,
            self.truncations,
            self.info,
        )
                
    def decode_action(self, encoded_action):
        # Decode back to the original action tuple        
        turn_input = encoded_action % 5
        level_input = (encoded_action // 5.0) % 5
        fire_input = (encoded_action // 25.0) % 2
        return np.array([fire_input, level_input, turn_input])


    