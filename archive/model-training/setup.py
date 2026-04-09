from setuptools import setup, find_packages

# Read the contents of the requirements.txt file
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='weibo-sentiment-model-training',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='A package for training Weibo sentiment analysis models.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/your-username/weibo-sentiment-analysis',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=requirements,
    python_requires='>=3.8',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'train-bert=scripts.train_bert:main',
            'train-lstm=scripts.train_lstm:main',
            'evaluate-model=scripts.evaluate:main',
            'export-model=scripts.export_model:main',
        ],
    },
)
