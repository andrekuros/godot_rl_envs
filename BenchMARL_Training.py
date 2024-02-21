#%%%

from benchmarl.environments import VmasTask
from benchmarl.environments import PettingZooTask
import torch

from benchmarl.environments.godotrl import b_ace

from benchmarl.experiment import Experiment, ExperimentConfig
from benchmarl.models.mlp import MlpConfig
from benchmarl.algorithms import IppoConfig, IqlConfig, QmixConfig, VdnConfig, VdnConfig, MappoConfig, MaddpgConfig

if __name__ == "__main__":
    
    # Loads from "benchmarl/conf/experiment/base_experiment.yaml"
    experiment_config = ExperimentConfig.get_from_yaml()

    experiment_config.sampling_device = 'cpu'
    experiment_config.train_device = 'cuda'
    experiment_config.prefer_continuous_actions = True
    experiment_config.evaluation_interval = 18000

    experiment_config.checkpoint_interval = 18000

    # experiment_config.exploration_eps_init = 1.0
    # experiment_config.exploration_eps_end = 1.0
    # experiment_config.evaluation = True  # Enable evaluation mode
    experiment_config.evaluation_episodes = 20
        
    # experiment_config.restore_file = "ippo_b_ace_mlp__49bcf045_24_02_20-15_18_29/checkpoints/checkpoint_144000.pt"
    # experiment_config.loggers = []
    
    experiment_config.on_policy_n_envs_per_worker = 4
    experiment_config.off_policy_n_envs_per_worker = 4

    # Loads from "benchmarl/conf/task/vmas/balance.yaml"
    # task = PettingZooTask.SIMPLE_REFERENCE.get_from_yaml()
    # task.config['max_cycles'] = 25
    # task.config['N'] = 9
    # task = VmasTask.SIMPLE_SPREAD.get_from_yaml()
    task = b_ace.B_ACE.b_ace.get_from_yaml()
    
    print(task)

    # Loads from "benchmarl/conf/algorithm/mappo.yaml"
    # algorithm_config = MappoConfig.get_from_yaml()

    algorithm_config = IppoConfig.get_from_yaml()

    # Loads from "benchmarl/conf/model/layers/mlp.yaml"
    model_config = MlpConfig.get_from_yaml()
    critic_model_config = MlpConfig.get_from_yaml()

    for i in range (1):
        experiment = Experiment(
            task=task,
            algorithm_config=algorithm_config,
            model_config=model_config,
            critic_model_config=critic_model_config,
            seed=i,
            config=experiment_config
        )
        experiment.run()
# %%
