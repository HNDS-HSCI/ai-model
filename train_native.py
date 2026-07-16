"""
train_native.py — HSCI Native Self-Training Entry Point
Run this script to train HSCI's neural components from scratch.
Uses Z3 proofs as the only training signal — no human labels needed.

Usage:
  python train_native.py                  # 100 epochs, auto-save
  python train_native.py --epochs 200     # 200 epochs
  python train_native.py --benchmark      # Quick benchmark without training
  python train_native.py --stats          # Show saved weight stats
"""
import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="HSCI Native Self-Training — proof-guided neural learning"
    )
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--samples", type=int, default=20, help="Samples per epoch")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark only (no training)")
    parser.add_argument("--stats", action="store_true", help="Show saved weight stats and exit")
    parser.add_argument("--verbose", action="store_true", help="Verbose per-sample output")
    args = parser.parse_args()

    # Show stats without initializing full system
    if args.stats:
        from hsci.training.weight_persistence import WeightPersistence
        wp = WeightPersistence()
        stats = wp.inspect()
        if stats:
            print("\n📊 HSCI Saved Weight Stats:")
            for k, v in stats.items():
                print(f"  {k}: {v}")
        else:
            print("No saved weights found. Run training first.")
        return

    print("\n🚀 Initializing HSCI v3.0 (Native Neurosymbolic Architecture)...")
    from hsci.core.rir_loop import RIRLoop
    from hsci.training.native_trainer import NativeTrainer

    # Initialize without LLM (fully native)
    rir = RIRLoop(use_llm=False)
    trainer = NativeTrainer(rir)

    if args.benchmark:
        print("\n📊 Running benchmark (no training)...")
        results = trainer.benchmark()
        print(f"\nBenchmark Results:")
        print(f"  Accuracy:  {results['accuracy']:.1%}")
        print(f"  Verified:  {results['verified']} / {results['total']}")
        return

    # Full training
    trainer.train(
        epochs=args.epochs,
        samples_per_epoch=args.samples,
        verbose_every=max(1, args.epochs // 10),
        save_weights=True
    )

    # Save weights at the end
    print("\n💾 Saving neural weights...")
    rir.save_weights()

    # Print final neural stats
    stats = rir.get_neural_stats()
    print("\n📊 Final Neural Stats:")
    print(f"  Weight version:   {stats['weight_version']}")
    print(f"  Proofs processed: {stats['classifier']['proof_count']}")
    print(f"  Average loss:     {stats['classifier']['avg_loss']:.4f}")
    print("\n✅ HSCI is now a trained, self-contained AI system.")
    print("   Next run will auto-load these weights and start smarter.\n")


if __name__ == "__main__":
    main()
