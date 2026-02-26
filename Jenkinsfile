pipeline {
    agent any

    environment {
        GIT_REPO_URL      = 'https://github.com/klis192/food-bot.git'
        GIT_CREDENTIALS   = 'github-token'
        BASE_BRANCH       = 'main'
        TELEGRAM_CHAT_ID  = '1038486996'
        TELEGRAM_CREDS_ID = 'telegram-bot-token'
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
                        sh '''
                            git config user.email "jenkins@ci.local"
                            git config user.name "Jenkins CI"
                        '''
                        sh "git checkout -b ${newBranch}"
                        sh 'git push https://$GIT_USER:$GIT_TOKEN@github.com/klis192/food-bot.git ' + newBranch
                        echo "Branch '${newBranch}' successfully pushed."
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline completed. New branch: tested/${env.BUILD_NUMBER}"
            withCredentials([string(credentialsId: env.TELEGRAM_CREDS_ID, variable: 'TG_TOKEN')]) {
                sh '''
                    curl -s -X POST https://api.telegram.org/bot$TG_TOKEN/sendMessage \
                        -d chat_id=$TELEGRAM_CHAT_ID \
                        -d parse_mode=HTML \
                        -d text="✅ <b>food-bot CI</b>%0ABuild <b>#$BUILD_NUMBER</b> прошёл успешно%0AВетка: <code>tested/$BUILD_NUMBER</code>"
                '''
            }
        }
        failure {
            echo "Tests FAILED. Branch was NOT created."
            withCredentials([string(credentialsId: env.TELEGRAM_CREDS_ID, variable: 'TG_TOKEN')]) {
                sh '''
                    curl -s -X POST https://api.telegram.org/bot$TG_TOKEN/sendMessage \
                        -d chat_id=$TELEGRAM_CHAT_ID \
                        -d parse_mode=HTML \
                        -d text="❌ <b>food-bot CI</b>%0ABuild <b>#$BUILD_NUMBER</b> упал%0AВетка <code>tested/$BUILD_NUMBER</code> не создана"
                '''
            }
        }
        cleanup {
            sh 'rm -rf .venv food_bot.db'
        }
    }
}
