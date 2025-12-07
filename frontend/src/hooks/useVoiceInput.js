/**
 * 语音输入 Hook
 * 
 * 使用 Web Speech API 进行语音识别
 */

import { useState, useRef, useCallback } from 'react';

export function useVoiceInput(onResult) {
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);

    const startListening = useCallback(() => {
        // 检查浏览器支持
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('抱歉，您的浏览器不支持语音识别功能，请尝试 Chrome 或 Edge 浏览器。');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.lang = 'zh-CN'; // 中文
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            setIsListening(true);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            setIsListening(false);
            if (event.error === 'not-allowed') {
                alert('请允许麦克风权限以使用语音功能。');
            }
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript && onResult) {
                onResult(transcript);
            }
        };

        recognitionRef.current = recognition;
        recognition.start();
    }, [onResult]);

    const stopListening = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        setIsListening(false);
    }, []);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    return {
        isListening,
        startListening,
        stopListening,
        toggleListening,
    };
}

export default useVoiceInput;
