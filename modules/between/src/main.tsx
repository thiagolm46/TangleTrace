import {createRoot} from 'react-dom/client'
import {BaseStyles, ThemeProvider} from '@primer/react'
import '@primer/primitives/dist/css/functional/themes/light.css'
import '@primer/primitives/dist/css/functional/themes/dark.css'
import '@primer/primitives/dist/css/functional/size/size.css'
import {App} from './App'
import {AppModel} from './model'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('The application root is missing.')

createRoot(root).render(
  <ThemeProvider colorMode="auto" dayScheme="light" nightScheme="dark">
    <BaseStyles><App model={new AppModel()} /></BaseStyles>
  </ThemeProvider>,
)
