import numpy as np
import tensorflow as tf 
from tensorflow.keras import layers
from collections import deque

class Actor(tf.keras.Model):
    def __init__(self, state_dim, action_dim):
        super(Actor, self).__init__()
        self.fc1 = layers.Dense(512, activation='relu')
        self.fc2 = layers.Dense(512, activation='relu')
        self.output_layer = layers.Dense(action_dim, activation='sigmoid')

    def call(self, state):
        x = self.fc1(state)
        x = self.fc2(x)
        return self.output_layer(x)


class Critic(tf.keras.Model):
    def __init__(self, state_dim, action_dim):
        super(Critic, self).__init__()
        self.s_fc1 = layers.Dense(512, activation='relu')
        self.a_fc1 = layers.Dense(512, activation='relu')
        self.combine_layer = layers.Concatenate()
        self.fc2 = layers.Dense(512, activation='relu')
        self.output_layer = layers.Dense(1)

    def call(self, state_action):
        state, action = state_action
        s = self.s_fc1(state)
        a = self.a_fc1(action)
        x = self.combine_layer([s, a])
        x = self.fc2(x)
        return self.output_layer(x)


class DDPGAgent:
    def __init__(self, state_dim, action_dim):
        self.actor = Actor(state_dim, action_dim)
        self.target_actor = Actor(state_dim, action_dim)
        self.critic = Critic(state_dim, action_dim)
        self.target_critic = Critic(state_dim, action_dim)
        self.actor_optimizer = tf.optimizers.Adam(learning_rate=0.001)
        self.critic_optimizer = tf.optimizers.Adam(learning_rate=0.002)
        self.buffer = deque(maxlen=10000)
        self.gamma = 0.99
        self.tau = 0.001

    def update_target_networks(self):
        actor_weights = self.actor.get_weights()
        target_actor_weights = self.target_actor.get_weights()
        critic_weights = self.critic.get_weights()
        target_critic_weights = self.target_critic.get_weights()

        for i in range(len(target_actor_weights)):
            target_actor_weights[i] = self.tau * actor_weights[i] + (1 - self.tau) * target_actor_weights[i]

        for i in range(len(target_critic_weights)):
            target_critic_weights[i] = self.tau * critic_weights[i] + (1 - self.tau) * target_critic_weights[i]

        self.target_actor.set_weights(target_actor_weights)
        self.target_critic.set_weights(target_critic_weights)

    def train_step(self, batch_size=64):
        if len(self.buffer) < batch_size:
            return

        minibatch = np.random.choice(len(self.buffer), batch_size, replace=False)
        states, actions, rewards, next_states = zip(*[self.buffer[i] for i in minibatch])

        states = np.vstack(states)
        actions = np.vstack(actions)
        rewards = np.vstack(rewards)
        next_states = np.vstack(next_states)

        with tf.GradientTape() as tape:
            target_actions = self.target_actor(next_states)
            target_values = rewards + self.gamma * self.target_critic([next_states, target_actions])

            critic_values = self.critic([states, actions])
            critic_loss = tf.reduce_mean(tf.square(target_values - critic_values))

        critic_gradients = tape.gradient(critic_loss, self.critic.trainable_variables)
        self.critic_optimizer.apply_gradients(zip(critic_gradients, self.critic.trainable_variables))

        with tf.GradientTape() as tape:
            actions_pred = self.actor(states)
            actor_loss = -tf.reduce_mean(self.critic([states, actions_pred]))

        actor_gradients = tape.gradient(actor_loss, self.actor.trainable_variables)
        self.actor_optimizer.apply_gradients(zip(actor_gradients, self.actor.trainable_variables))

    def act(self, state):
        state_tensor = tf.convert_to_tensor(state.reshape(1, -1), dtype=tf.float32)
        return self.actor(state_tensor).numpy()[0]
    
    def remember(self, state, action, reward, next_state):
        self.buffer.append((state, action, reward, next_state))
