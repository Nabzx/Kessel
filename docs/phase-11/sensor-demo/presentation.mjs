import {present as controlPresent,command} from '../harvest-demo/presentation.mjs';
export {command};
export function ghostForecast(forecast,inspect=false) {
  if (!forecast || forecast.source !== 'sensor_observation_residual_ensemble' || !forecast.input_usable || !inspect) return null;
  if (!Array.isArray(forecast.render_pose) || forecast.render_pose.length !== 7 || !forecast.render_pose.every(Number.isFinite)) return null;
  return {pose:forecast.render_pose,load:forecast.observation.proprio[8]};
}
export function present(run,frame) {
  const value=controlPresent(run,{...frame,forecast:null}),f=frame.forecast,e=f?.measured_error;
  const reason=!f?'No decision forecast yet.':!f.input_usable?'Range unavailable; forecast hidden.':!e?'Partial terminal interval: outside the 0.1 s sensor horizon.':'Compared with the next received numeric observation; position error includes sensor noise.';
  return {...value,forecastStatus:`Experimental predictor failed fresh qualification. ${reason}`,
    positionError:e?`${(e.position_m*1000).toFixed(2)} mm`:'Not measured',loadError:e?`${e.carried_kg.toFixed(2)} kg`:'Not measured'};
}
