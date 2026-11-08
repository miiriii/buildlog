import { useState } from 'react'

function App() {
  const [result, setResult] = useState('아직 실행하지 않았습니다.')

  function runPractice() {
    try {
      setResult(welcomeMessage)
    } catch (error) {
      console.error(error)
      setResult(`${error.name}: ${error.message}`)
    }
  }

  return (
    <main>
      <h1>오류 확인 실습</h1>
      <p>기존 BuildLog와 연결되지 않는 독립 실습 화면입니다.</p>
      <button type="button" onClick={runPractice}>실행하기</button>
      <hr />
      <strong>실행 결과</strong>
      <pre>{result}</pre>
    </main>
  )
}

export default App