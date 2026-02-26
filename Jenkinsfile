pipeline {
    agent any

    environment {
        GIT_REPO_URL    = 'https://github.com/klis192/food-bot.git'
        GIT_CREDENTIALS = 'github-token'   // ID credentials в Jenkins
        BASE_BRANCH     = 'main'
    }

    triggers {
        // Опрашивать репо каждые 5 минут на новые коммиты
        pollSCM('H/5 * * * *')
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Cloning ${env.GIT_REPO_URL} (branch: ${env.BASE_BRANCH})"
                git branch: env.BASE_BRANCH,
                    credentialsId: env.GIT_CREDENTIALS,
                    url: env.GIT_REPO_URL
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements.txt
                    pip install --quiet pytest pytest-cov
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/ \
                        --tb=short \
                        --junitxml=test-results.xml \
                        --cov=. \
                        --cov-report=xml:coverage.xml \
                        -v
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Create Tested Branch') {
            when {
                expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
            }
            steps {
                script {
                    def newBranch = "tested/${env.BUILD_NUMBER}"
                    echo "Tests passed! Creating branch: ${newBranch}"

                    withCredentials([usernamePassword(
                        credentialsId: env.GIT_CREDENTIALS,
                        usernameVariable: 'GIT_USER',
                        passwordVariable: 'GIT_TOKEN'
                    )]) {
                        sh """
                            git config user.email "jenkins@ci.local"
                            git config user.name "Jenkins CI"

                            git checkout -b ${newBranch}
                            git push https://${GIT_USER}:${GIT_TOKEN}@github.com/klis192/food-bot.git ${newBranch}

                            echo "Branch '${newBranch}' successfully pushed."
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline completed. New branch: tested/${env.BUILD_NUMBER}"
        }
        failure {
            echo "Tests FAILED. Branch was NOT created."
        }
        cleanup {
            sh 'rm -rf .venv food_bot.db'
        }
    }
}
