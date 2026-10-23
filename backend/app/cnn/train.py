"""python -m app.cnn.train  ->  models/cnn.pt (synthetic bootstrap; fine-tune on labelled incidents)."""
import numpy as np
import torch
import torch.nn as nn

from app.cnn.model import CLASSES, WEIGHTS, _net, synth


def make(n_per_class: int, seed: int):
    rng = np.random.default_rng(seed)
    X = [synth(k, rng) for k in CLASSES for _ in range(n_per_class)]
    y = [i for i in range(len(CLASSES)) for _ in range(n_per_class)]
    return torch.tensor(np.stack(X))[:, None], torch.tensor(y)


def main(epochs: int = 15):
    torch.manual_seed(0)
    Xtr, ytr = make(300, 1)
    Xva, yva = make(60, 2)
    net, opt, loss_fn = _net(), None, nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(net.parameters(), 2e-3)
    for ep in range(epochs):
        net.train()
        for idx in torch.randperm(len(Xtr)).split(64):
            opt.zero_grad()
            loss_fn(net(Xtr[idx]), ytr[idx]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            acc = (net(Xva).argmax(1) == yva).float().mean().item()
        print(f"epoch {ep + 1:02d} val_acc={acc:.3f}")
    WEIGHTS.parent.mkdir(exist_ok=True)
    torch.save(net.state_dict(), WEIGHTS)
    print("saved", WEIGHTS)


if __name__ == "__main__":
    main()
