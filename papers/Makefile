.PHONY: all test benchmark validate paper clean

all: test benchmark validate paper

test:
	pytest hsci/tests/ -v

benchmark:
	python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"

validate:
	pytest scratch/test_hsci_pub_2_consistency.py -v

paper:
	pdflatex -interaction=nonstopmode papers/HSCI_Paper.tex || true
	bibtex HSCI_Paper || true
	pdflatex -interaction=nonstopmode papers/HSCI_Paper.tex || true
	pdflatex -interaction=nonstopmode papers/HSCI_Paper.tex || true

clean:
	rm -rf *.aux *.log *.bbl *.blg *.out results/*.json results/*.csv
