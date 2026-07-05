import { type QueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import { getGlobalModelInfo } from '@/hermes'
import { useI18n } from '@/i18n'
import { notifyError } from '@/store/notifications'
import {
  $activeSessionId,
  $currentExcitechGatewayAgent,
  $currentExcitechGatewayDomain,
  $currentExcitechGatewayMode,
  $currentModel,
  $currentProvider,
  setCurrentExcitechGatewayAgent,
  setCurrentExcitechGatewayDomain,
  setCurrentExcitechGatewayMode,
  setCurrentModel,
  setCurrentProvider
} from '@/store/session'
import type { ModelOptionsResponse } from '@/types/hermes'

interface ModelSelection {
  excitechGatewayAgent?: string
  excitechGatewayDomain?: string
  excitechGatewayMode?: string
  model: string
  provider: string
}

interface ModelControlsOptions {
  activeSessionId: string | null
  queryClient: QueryClient
  requestGateway: <T = unknown>(method: string, params?: Record<string, unknown>) => Promise<T>
}

export function useModelControls({ activeSessionId, queryClient, requestGateway }: ModelControlsOptions) {
  const { t } = useI18n()
  const copy = t.desktop

  const updateModelOptionsCache = useCallback(
    (provider: string, model: string, includeGlobal: boolean) => {
      const patch = (prev: ModelOptionsResponse | undefined) => ({ ...(prev ?? {}), provider, model })

      queryClient.setQueryData<ModelOptionsResponse>(['model-options', activeSessionId || 'global'], patch)

      if (includeGlobal) {
        queryClient.setQueryData<ModelOptionsResponse>(['model-options', 'global'], patch)
      }
    },
    [activeSessionId, queryClient]
  )

  // Seed the composer's model state from the profile default. `force` reseeds
  // for a profile swap (the new profile has its own default); otherwise this
  // only fills an EMPTY selection so a user's pick (plain UI state in
  // $currentModel) survives the lifecycle refreshes that fire on boot / fresh
  // draft / session events. A live session owns the footer, so skip entirely.
  const refreshCurrentModel = useCallback(async (force = false) => {
    try {
      if ($activeSessionId.get()) {
        return
      }

      if (!force && $currentModel.get()) {
        return
      }

      const result = await getGlobalModelInfo()

      if ($activeSessionId.get() || (!force && $currentModel.get())) {
        return
      }

      if (typeof result.model === 'string') {
        setCurrentModel(result.model)
      }

      if (typeof result.provider === 'string') {
        setCurrentProvider(result.provider)
      }
    } catch {
      // The delayed session.info event still updates this once the agent is ready.
    }
  }, [])

  // Returns whether the switch succeeded so callers can await it before applying
  // follow-up changes. The composer model is plain UI state: with no live
  // session it's just stored (and shipped on the next session.create); with one
  // it's scoped to that session via config.set. It NEVER writes the profile
  // default — that lives in Settings → Model — so picking a model here can't
  // silently mutate global config.
  const selectModel = useCallback(
    async (selection: ModelSelection): Promise<boolean> => {
      // Snapshot for rollback: the switch is applied optimistically, so a
      // failure must restore the prior model/provider (store + query cache)
      // rather than leave the UI showing a model the backend never selected.
      const nextExcitechMode = (selection.excitechGatewayMode || 'openai-proxy').trim() || 'openai-proxy'
      const nextExcitechDomain = (selection.excitechGatewayDomain || 'general').trim() || 'general'
      const nextExcitechAgent = (selection.excitechGatewayAgent || 'assistant').trim() || 'assistant'
      const prevModel = $currentModel.get()
      const prevProvider = $currentProvider.get()
      const prevExcitechMode = $currentExcitechGatewayMode.get()
      const prevExcitechDomain = $currentExcitechGatewayDomain.get()
      const prevExcitechAgent = $currentExcitechGatewayAgent.get()

      setCurrentModel(selection.model)
      setCurrentProvider(selection.provider)
      setCurrentExcitechGatewayMode(nextExcitechMode)
      setCurrentExcitechGatewayDomain(nextExcitechDomain)
      setCurrentExcitechGatewayAgent(nextExcitechAgent)
      updateModelOptionsCache(selection.provider, selection.model, !activeSessionId)

      // No live session yet: the pick is pure UI state. session.create reads
      // $currentModel/$currentProvider and applies it as that session's override.
      if (!activeSessionId) {
        return true
      }

      try {
        await requestGateway('config.set', {
          session_id: activeSessionId,
          key: 'model',
          value: `${selection.model} --provider ${selection.provider}`
        })

        if (selection.provider === 'excitech-gateway') {
          await requestGateway('config.set', {
            session_id: activeSessionId,
            key: 'excitech_gateway_mode',
            value: nextExcitechMode
          })
          await requestGateway('config.set', {
            session_id: activeSessionId,
            key: 'excitech_gateway_domain',
            value: nextExcitechDomain
          })
          await requestGateway('config.set', {
            session_id: activeSessionId,
            key: 'excitech_gateway_agent',
            value: nextExcitechAgent
          })
        }

        void queryClient.invalidateQueries({ queryKey: ['model-options', activeSessionId] })

        return true
      } catch (err) {
        setCurrentModel(prevModel)
        setCurrentProvider(prevProvider)
        setCurrentExcitechGatewayMode(prevExcitechMode)
        setCurrentExcitechGatewayDomain(prevExcitechDomain)
        setCurrentExcitechGatewayAgent(prevExcitechAgent)
        updateModelOptionsCache(prevProvider, prevModel, !activeSessionId)
        notifyError(err, copy.modelSwitchFailed)

        return false
      }
    },
    [activeSessionId, copy.modelSwitchFailed, queryClient, requestGateway, updateModelOptionsCache]
  )

  return { refreshCurrentModel, selectModel, updateModelOptionsCache }
}
