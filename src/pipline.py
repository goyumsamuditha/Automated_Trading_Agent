import subprocess, sys

steps = [
    ('market analysis', 'src/market_analysis.py'),
    ('Information Retreval', 'src/info_retrieval.py'),
    ('Model Train', 'src/decision_engine.py'),
    ('Backtest', 'src/backtest.py'),
]

for name , script in steps:
    print(f'\n{"="*50}') # Print a separator for better readability
    print(f'Running {name} step...') # Print the name of the current step being executed
    print(f'{"="*50}') # Print another separator
    result = subprocess.run([sys.executable, script], capture_output=False) # Run the script using the same Python interpreter and capture output
    if result.returncode != 0: # Check if the script execution was successful
        print(f'Error occurred during {name} step. Exiting pipeline.') # Print an error message if the script failed
        sys.exit(1) # Exit the pipeline with a non-zero status to indicate failure


print('\nPipeline execution completed successfully!') # Print a success message after all steps have been executed
