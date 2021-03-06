import torch.nn.functional as F
from torch import nn


class EmbeddingDropout(nn.Module):
    def __init__(self, embedding, dropout=0.1, scale=None):
        super().__init__()
        self.embedding = embedding
        self.dropout = dropout
        self.scale = scale

    def forward(self, words):
        if self.dropout > 0 and self.training:
            weight = self.embedding.weight
            mask = weight.new_empty((weight.size(0), 1)) \
                       .bernoulli_(1 - self.dropout) \
                       .expand_as(weight).div(1 - self.dropout)
            masked_embed_weight = mask * weight
        else:
            masked_embed_weight = self.embedding.weight

        if self.scale is not None:
            masked_embed_weight = self.scale.expand_as(masked_embed_weight) * masked_embed_weight

        X = F.embedding(
            words, masked_embed_weight, self.embedding.padding_idx, self.embedding.max_norm,
            self.embedding.norm_type, self.embedding.scale_grad_by_freq, self.embedding.sparse)

        return X


class StaticDropout(nn.Module):
    # Currently not in use. Was used as part of gradient checkpointing, to statically generate a dropout mask
    # Since torch builtin checkpointing (supposedly) handles RNG state, we are currently not using static dropout

    def __init__(self, p=0.5):
        super().__init__()
        if not 0 <= p <= 1:
            raise ValueError('Dropout probability has to be between 0 and 1, but got {:f}'.format(p))
        self.p = p
        self.noise = None

    def gen_noise(self, inputs):
        self.noise = inputs.new().resize_as_(inputs)
        if self.p == 1:
            self.noise.fill_(0)
        else:
            self.noise.bernoulli_(1 - self.p).div_(1 - self.p)
        self.noise = self.noise.expand_as(inputs)

    def forward(self, inputs):
        if self.training:
            if self.noise is None:
                self.gen_noise(inputs)
            return inputs * self.noise
        else:
            return inputs

    def reset_state(self):
        self.noise = None

    def extra_repr(self):
        return 'p={:f}'.format(self.p)
